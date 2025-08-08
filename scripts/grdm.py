# GRDM Test on Playwright ユーティリティ関数群

import asyncio
import base64
import os
import re
import time
import traceback
from playwright.async_api import expect


async def login_cas(page, username, password):
    # find_element_by_xpath_with_retry(driver, '').send_keys(username)
    # find_element_by_xpath_with_retry(driver, '//input[@name = "password"]').send_keys(password)
    # find_element_by_xpath_with_retry(driver, '//input[@type = "submit"]').click()
    await page.locator('//input[@name = "username"]').fill(username);
    await page.locator('//input[@name = "password"]').fill(password);
    await page.locator('//input[@type = "submit"]').click();

async def login_fakecas(page, username):
    """FakeCAS用のログイン処理"""
    # ユーザー名を入力
    await page.locator('#username').fill(username)
    # Sign Inボタンをクリック
    await page.locator('#submit').click()

async def expect_idp_login(page, idp_name, timeout=30000):
    # Shibboleth Login Page
    login_page_locators = _get_login_page_locators(idp_name)
    await expect(page.locator(login_page_locators['username'])).to_be_editable(timeout=timeout)

async def login_as_admin(page, idp_name, idp_username, idp_password, transition_timeout=30000):
    if idp_name is None:
        # CASでログイン
        await page.locator('#id_email').fill(idp_username)
        await page.locator('#id_password').fill(idp_password)
        await page.locator('//button[text() = "サインイン"]').click()
        return
    try:
        # IdPリストから所望のIdPを選択
        idplist = page.locator('//form[@id = "IdPList"]//input[@type = "text"]')
        await idplist.fill(idp_name);
        await idplist.press('Enter');
        await page.locator(f'//div[@class = "select" and text() = "{idp_name}"]').click()
    
        # 選択ボタンが有効になったことを確認
        locator_wayf_submit = page.locator('//input[@id = "wayf_submit_button"]')
        await expect(locator_wayf_submit).to_be_enabled(timeout=transition_timeout)
        await locator_wayf_submit.click()

        # アカウント入力欄が編集可能になったことを確認
        await expect_idp_login(page, idp_name, timeout=transition_timeout)

        await _login_idp_pw(page, idp_name, idp_username, idp_password, transition_timeout=transition_timeout)
    except:
        traceback.print_exc()

        print('ユーザー名とパスワードによるログインを試みます...')
        # すでにIdP選択済みとみなし、ユーザー名とパスワード入力を試みる
        await _login_idp_pw(page, idp_name, idp_username, idp_password, transition_timeout=transition_timeout)

async def login(page, idp_name, idp_username, idp_password, transition_timeout=30000):
    if idp_name is None:
        # CASでログイン
        if '/login' not in page.url:
            # 現在CAS以外→一旦ログインボタンを押す
            await page.locator('//button[text() = "ログイン"]').click()
        await login_cas(page, idp_username, idp_password)
        return
    
    # FakeCASの場合の処理
    if idp_name == 'FakeCAS':
        # FakeCAS(port 8080)でない場合のみサインインボタンをクリック
        if ':8080' not in page.url:
            await page.locator('//button[@data-test-sign-in-button]').click()
        await login_fakecas(page, idp_username)
        return
    
    # 通常のIdP選択フロー（GakuNin RDM IdP, Orthrosなど）
    try:
        await page.locator('//*[@id = "dropdown_img"]').click()

        # IdPが要素として作成されることを確認
        locator = page.locator(f'//*[@class = "list_idp" and text() = "{idp_name}"]')
        await expect(locator).to_be_visible(timeout=transition_timeout)
        time.sleep(5)
        await locator.click()

        # 選択ボタンが有効になったことを確認
        locator_wayf_submit = page.locator('//input[@id = "wayf_submit_button"]')
        await expect(locator_wayf_submit).to_be_enabled(timeout=transition_timeout)
        await locator_wayf_submit.click()

        # アカウント入力欄が編集可能になったことを確認
        await expect_idp_login(page, idp_name, timeout=transition_timeout)

        await _login_idp_pw(page, idp_name, idp_username, idp_password, transition_timeout=transition_timeout)
    except:
        traceback.print_exc()

        print('ユーザー名とパスワードによるログインを試みます...')
        # すでにIdP選択済みとみなし、ユーザー名とパスワード入力を試みる
        await _login_idp_pw(page, idp_name, idp_username, idp_password, transition_timeout=transition_timeout)

async def _login_idp_pw(page, idp_name, idp_username, idp_password, transition_timeout=30000):
    # Shibboleth Login Page
    login_page_locators = _get_login_page_locators(idp_name)

    username_fields = await page.locator(login_page_locators['username']).count()
    if username_fields > 0:
        # ユーザー名入力を求められた
        password_fields = await page.locator(login_page_locators['password']).count()
        submit_buttons = await page.locator(login_page_locators['submit']).count()
        assert username_fields == 1 and password_fields == 1 and submit_buttons == 1, (username_fields, password_fields, submit_buttons)
        # メールアドレスとパスワードを入力
        await page.locator(login_page_locators['username']).fill(idp_username)
        await page.locator(login_page_locators['password']).fill(idp_password)
    
        # サインインボタンが押下可能であることを確認
        await expect(page.locator(login_page_locators['submit'])).to_be_enabled(timeout=transition_timeout)
        # サインインボタンをクリック
        await page.locator(login_page_locators['submit']).click()

    if idp_name == 'GakuNin RDM IdP':
        # チェック「Ask me again at next login」が表示されることを確認
        await expect(page.locator('#_shib_idp_doNotRememberConsent')).to_be_enabled(timeout=transition_timeout)
        await page.locator('#_shib_idp_doNotRememberConsent').click()
        await expect(page.locator('#_shib_idp_doNotRememberConsent')).to_be_checked()
    
        await expect(page.locator('//*[@name="_eventId_proceed"]')).to_be_enabled()
        await page.locator('//*[@name="_eventId_proceed"]').click()
    else:
        # Orthros
        await expect(page.locator('#consentOnce')).to_be_enabled(timeout=transition_timeout)
        await page.locator('#consentOnce').click()

        await expect(page.locator('#continue')).to_be_enabled()
        await page.locator('#continue').click()

def _get_login_page_locators(idp_name):
    if idp_name == 'GakuNin RDM IdP':
        return {
            'username': '#username',
            'password': '#password',
            'submit': '//button[@type = "submit"]'
        }
    return {
        'username': '#signInName',
        'password': '#password',
        'submit': '#next'
    }

async def expect_dashboard(page, transition_timeout=30000, retries=3):
    # 429 Too many requestsで表示できない場合があるので、複数回リロードする
    remain = retries
    while remain > 0:
        try:
            # GRDMのボタンが表示されることを確認
            await expect(page.locator('//*[text() = "プロジェクト管理者"]')).to_be_visible(timeout=transition_timeout)
            break
        except:
            if remain <= 0:
                raise
            remain -= 1
            traceback.print_exc()
            print('Retrying...')
            # 1分待って再チャレンジ
            await asyncio.sleep(60)            
    
async def ensure_project_exists(page, project_name, transition_timeout=30000):
    await expect(page.locator('//*[@data-test-create-project-modal-button]')).to_have_count(1, timeout=transition_timeout)
    try:
        await expect(page.locator(f'//*[@data-test-dashboard-item-title and text()="{project_name}"]')).to_be_visible()
        return False
    except:
        # プロジェクトが存在しない
        await page.locator('//*[@data-test-create-project-modal-button]').click()

        # プロジェクト名フィールドが表示される
        await expect(page.locator('//input[contains(@class, "project-name")]')).to_be_editable(timeout=transition_timeout)
        time.sleep(1)

        # プロジェクト名を入力
        await page.locator('//input[contains(@class, "project-name")]').fill(project_name)
    
        # 作成ボタンが有効化される
        create_button_locator = page.locator('//*[@data-test-create-project-submit]')
        await expect(create_button_locator).to_be_enabled()
    
        # 作成ボタンをクリック
        await create_button_locator.click()
    
        await expect(page.locator('//button[@data-test-stay-here]')).to_be_visible(timeout=transition_timeout)
        await page.locator('//button[@data-test-stay-here]').click()
        
        # プロジェクトダッシュボードが更新され、
        # GRDMのボタンが表示されることを確認
        await expect(page.locator('//*[text() = "プロジェクト管理者"]')).to_be_visible(timeout=transition_timeout)
        await expect(page.locator(f'//*[@data-test-dashboard-item-title and text()="{project_name}"]')).to_be_visible(timeout=transition_timeout)
        return True    

async def delete_project(page, transition_timeout=30000):
    await page.locator(f'//ul[contains(@class, "navbar-nav")]//a[text() = "設定"]').click()
    await asyncio.sleep(3)
    await page.locator('//button[text() = "プロジェクトを削除" and @data-target = "#nodesDelete"]').click()

    confirmation_label = page.locator('//strong[@data-bind = "text: confirmationString"]')
    await expect(confirmation_label).to_have_count(1, timeout=transition_timeout)
    confirmation = await confirmation_label.text_content()
    print(confirmation)

    time.sleep(1)
    confirmation_input = page.locator('//*[@data-bind = "editableHTML: {observable: confirmInput, onUpdate: handleEditableUpdate}"]')
    await confirmation_input.fill(confirmation)

    delete_button = page.locator('//a[contains(@class, "btn-danger") and text() = "削除"]')
    await expect(delete_button).to_be_visible()
    await delete_button.click()

def get_select_storage_title_locator(page, provider):
    return page.locator(get_select_storage_title_xpath(provider))

def get_select_storage_title_xpath(provider):
    return f'//*[contains(@class, "tb-td-first")]//*[contains(@style, "/static/addons/")]/../../following-sibling::*[contains(@class, "title-text")]//*[starts-with(text(), "{provider}")]'

def get_select_expanded_storage_title_locator(page, provider):
    return page.locator(get_select_expanded_storage_title_xpath(provider))

def get_select_expanded_storage_title_xpath(provider):
    return f'//*[contains(@class, "fa-minus")]/../..//*[contains(@style, "/static/addons/")]/../../following-sibling::*[contains(@class, "title-text")]//*[starts-with(text(), "{provider}")]'

def get_select_folder_title_locator(page, provider):
    return page.locator(get_select_folder_title_xpath(provider))

def get_select_folder_title_xpath(name):
    return f'//*[contains(@class, "tb-expand-icon-holder")]//i[contains(@class, "fa-folder")]/../../following-sibling::*[contains(@class, "title-text")]//*[text() = "{name}"]'

def get_select_folder_toggle_locator(page, provider, expanded=False, collapsed=False):
    return page.locator(get_select_folder_toggle_xpath(provider, expanded=expanded, collapsed=collapsed))

def get_select_folder_toggle_xpath(name, expanded=False, collapsed=False):
    base_xpath = f'//*[contains(@class, "title-text")]//*[text() = "{name}"]/../preceding-sibling::*[contains(@class, "tb-td-first")]//*[contains(@class, "tb-toggle-icon")]'
    if expanded:
        return f'{base_xpath}//i[contains(@class, "fa-minus")]'
    if collapsed:
        return f'{base_xpath}//i[contains(@class, "fa-plus")]'
    return base_xpath

def get_select_folder_droppable_locator(page, provider):
    return page.locator(get_select_folder_droppable_xpath(provider))

def get_select_folder_droppable_xpath(name):
    return f'//*[contains(@class, "tb-expand-icon-holder")]//i[contains(@class, "fa-folder")]/../../following-sibling::*[contains(@class, "title-text")]//*[text() = "{name}"]/../../..'

def get_select_folder_draggable_locator(page, provider):
    return page.locator(get_select_folder_draggable_xpath(provider))

def get_select_folder_draggable_xpath(name):
    return f'//*[contains(@class, "tb-expand-icon-holder")]//i[contains(@class, "fa-folder")]/../../following-sibling::*[contains(@class, "title-text")]//*[text() = "{name}"]/../..'

def get_select_file_title_locator(page, provider):
    return page.locator(get_select_file_title_xpath(provider))

def get_select_file_title_xpath(name):
    return f'//*[contains(@class, "tb-expand-icon-holder")]//*[contains(@class, "file-extension")]/../../following-sibling::*[contains(@class, "title-text")]//*[text() = "{name}"]'

def get_select_file_extension_locator(page, provider):
    return page.locator(get_select_file_extension_xpath(provider))

def get_select_file_extension_xpath(name):
    return f'//*[contains(@class, "title-text")]//*[text() = "{name}"]/../preceding-sibling::*[contains(@class, "tb-td-first")]//*[contains(@class, "file-extension")]'

def get_select_file_draggable_locator(page, provider):
    return page.locator(get_select_file_draggable_xpath(provider))

def get_select_file_draggable_xpath(name):
    return f'//*[contains(@class, "tb-expand-icon-holder")]//*[contains(@class, "file-extension")]/../../following-sibling::*[contains(@class, "title-text")]//*[text() = "{name}"]/../..'

async def wait_for_uploaded(page, filename):
    await expect(page.locator(f'//*[text() = "{filename}"]/../following-sibling::*//*[@role = "progressbar"]')).to_have_count(0, timeout=30000)
    await expect(get_select_file_title_locator(page, filename)).to_be_visible(timeout=1000)    

def _bytes_to_data_url(byte_data, mime_type="application/octet-stream"):
    """バイト配列をDataURLに変換"""
    base64_data = base64.b64encode(byte_data).decode('utf-8')
    return f"data:{mime_type};base64,{base64_data}"

async def upload_file(page, path):
    # Upload ボタンを使ってファイルをアップロード
    await page.locator('//i[contains(@class, "fa-upload")]/../*[text() = "アップロード"]').click()
    await page.set_input_files('//input[@type = "file" and @class = "dz-hidden-input"]', path)

async def upload_folder(page, path):
    # フォルダのアップロード ボタンを使ってファイルをアップロード
    await page.locator('//i[contains(@class, "fa-plus")]/../*[text() = "フォルダのアップロード"]').click()
    await page.set_input_files('//input[@type = "file" and @webkitdirectory = "true"]', path)

async def drop_file(page, element_locator, path):
    # based on: https://zenn.dev/st_little/articles/how-to-upload-files-in-playwright
    with open(path, 'rb') as f:
        buffer = f.read()

    # ページのコンテキスト内でDataTransferとFileを作成
    data_transfer = await page.evaluate_handle(
        """async ({ bufferData, localFileName, localFileType }) => {
            const dt = new DataTransfer();
    
            const blobData = await fetch(bufferData).then((res) => res.blob());
    
            const file = new File([blobData], localFileName, {
            type: localFileType,
            });
            dt.items.add(file);
            return dt;
        }""",
        {
            'bufferData': _bytes_to_data_url(buffer),
            'localFileName': os.path.split(path)[-1],
            'localFileType': '',
        }
    )

    await page.dispatch_event(element_locator, 'drop', {
        'dataTransfer': data_transfer
    })
    await data_transfer.dispose()

async def drag_and_drop(page, source, dest):
    await expect(source).to_have_class(re.compile('.*ui-draggable.*'))
    await expect(dest).to_have_class(re.compile('.*ui-droppable.*'))

    center_coordinates_source = await source.evaluate('''element => {
        const rect = element.getBoundingClientRect();
        return {
            x: rect.left + rect.width / 2,
            y: rect.top + rect.height / 2
        };
    }''')

    center_coordinates_dest = await dest.evaluate('''element => {
        const rect = element.getBoundingClientRect();
        return {
            x: rect.left + rect.width / 2,
            y: rect.top + rect.height / 2
        };
    }''')

    await page.mouse.move(center_coordinates_source['x'], center_coordinates_source['y'])
    await page.mouse.down()
    await page.wait_for_timeout(1000)
    await page.mouse.move(center_coordinates_dest['x'], center_coordinates_dest['y'], steps=30)
    await page.wait_for_timeout(1000)
    await page.mouse.up()
