# Automation of GRDM Integration Testing

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/RCOSDP/RDM-e2e-test-nb/HEAD)

## Overview

This document describes the architecture and usage of GRDM integration test automation.

The purpose of this system is to provide an environment that can mechanically execute content equivalent to the current manual procedures for GRDM integration testing.

## Basic Idea

E2E tests (such as Playwright) are powerful tools for testing, but they have many parts that depend on UI structure and can break unexpectedly. When tests fail, it's difficult to accurately identify where they're failing, and even small UI changes often require test code modifications, leading to high maintenance costs.

Using [Jupyter Notebook](https://jupyter.org/) solves this problem. Since you can execute cell by cell, you can identify problem areas while executing step-by-step. You can visually track test progress by checking screenshots at each step. Even when tests fail, execution results up to the previous cell remain, making it easy to isolate problems. The interactive environment allows you to modify test code through trial and error, making maintenance work efficient.

### Use Cases

In software development, both "acceptance testing" to verify that new features and fixes work correctly, and "continuous testing (CI/CD)" that runs automatically with every code change are essential for quality assurance. Especially in OSS development and multi-vendor collaboration environments, CI/CD mechanisms that continuously verify that changes by different developers haven't broken existing functionality play an extremely important role in maintaining codebase quality.

However, traditionally these have often been implemented with separate tools and code, requiring dual management of test content in different formats. The innovative aspect of this automated integration testing is that a single test code written in Jupyter Notebook can be executed interactively when developers manually verify it, and the same code can be executed as-is in automated environments like GitHub Actions. In other words, tests that have been verified during development directly function as quality checks that will be automatically executed in the future.

This system is utilized in the following two main scenarios:

#### 1. Acceptance Testing During Feature Development

During verification after feature development or bug fixes, we maximize the interactive characteristics of Jupyter Notebook. Developers and testers can enjoy the following advantages:

- **Step-by-step execution**: Immediately identify problem areas by executing cell by cell
- **Visual confirmation**: Progress while checking screenshots at each step
- **Integration with external systems**: Tests including operations on external systems such as Google login are also possible

For usage in this scenario, see the [Integration Test Environment Architecture](#integration-test-environment-architecture) section and beyond for details.

#### 2. Automated Testing with CI/CD

By integrating into CI/CD pipelines like GitHub Actions and utilizing command-line execution with papermill, we achieve continuous quality assurance:

- **Automatic execution**: Tests run automatically on push or Pull Request
- **Batch processing**: Execute notebooks non-interactively using papermill
- **Parallel execution**: Run multiple test groups in parallel using matrix strategy
- **Result visualization**: Save execution results as Artifacts, viewable as videos and notebooks

For usage in this scenario, see the [CI/CD (GitHub Actions)](#cicd-github-actions) section for details.

Note that some notebooks requiring interactive input cannot be executed in CI environments, but in such cases we take the following measures:

- Inject values externally through parameterization
- Implement skip processing using conditional branching
- Prepare CI-specific alternative processing (e.g., mock authentication using FakeCAS)

#### Contributing to Quality Assurance

While it may be difficult to incorporate all acceptance tests directly into CI/CD, this system enables many tests to be incorporated into continuous testing. This achieves:

- **Automated regression testing**: Continuously confirm that existing functionality isn't broken by new changes
- **Early problem discovery**: Discover problems early in the development cycle, reducing fix costs
- **Development efficiency improvement**: Reduce manual testing effort and focus on more creative work

In this way, by contributing to quality assurance from both acceptance testing and CI/CD perspectives, we contribute to improving the stability and reliability of the GRDM codebase.

## CI/CD (GitHub Actions)

This repository uses GitHub Actions to automatically run E2E tests. Tests are automatically executed on push or pull request, continuously verifying the GRDM codebase behavior.

### Checking Test Results

After test execution, results can be checked from GitHub Actions Artifacts:

1. **test-results-failed** - Archive containing only failed test notebooks
   - Notebook (.ipynb) files where errors occurred
   - Related sub-notebooks and execution results
   - Minimal set of files needed for problem investigation

2. **test-results-full** - Complete archive containing all test results
   - All executed notebook (.ipynb) files
   - Screen capture videos (.webm format)
   - Execution results and evidence for each test step

### Video Verification

The execution process of each test is recorded as video (.webm format):
- Videos can be played directly in browsers
- You can visually confirm how each test step was executed
- You can accurately understand the screen state when errors occur

### Detailed Confirmation with Notebooks

Test result notebook files contain the following information:
- Execution results for each cell
- Error messages and stack traces
- Runtime parameters
- Screenshots (when errors occur)

By opening these notebooks in a Jupyter environment, you can check error details and re-execute or debug as needed.

## Integration Test Environment Architecture

The following software is used for GRDM integration test automation:

- OperationHub https://github.com/NII-cloud-operation/OperationHub
- papermill https://github.com/nteract/papermill
- Jenkins https://www.jenkins.io/

OperationHub is a JupyterHub customized for infrastructure operations, providing a development and execution environment for Jupyter Notebooks created for integration testing.
papermill is a library for mechanically executing Jupyter Notebooks from programs. It allows customizing Jupyter Notebook behavior by providing parameters at runtime. Using papermill's parameter feature, connection information about integration test targets and authentication information for storage can be provided externally.
Jenkins is a CI/CD tool for periodically executing Jupyter Notebooks created in OperationHub.

In this system, test performers can conduct integration tests as follows:

1. Test item development/maintenance: When developing or maintaining test items, create integration test Jupyter Notebooks on OperationHub. Create test scripts (retrieving elements displayed in the browser to verify display and behavior) through Jupyter Notebook's web UI. You can develop scripts iteratively through the Jupyter Notebook UI. It's also possible to write processes for collecting response performance or recording evidence about execution results.
2. Test item execution: Engineers executing test items run the test execution Jupyter Notebooks. papermill executes the Jupyter Notebook with the specified parameters.

Test execution, success/failure determination, and evidence collection are performed by Jupyter Notebooks. Since the Jupyter Notebook environment has data processing libraries such as pandas and numpy installed, analysis and visualization of test results are also easy.

## Test Unit Design

In automating integration testing, we designed test units. Since GRDM primarily provides storage services for managing research data to researchers, test items mainly focus on operations such as registering and retrieving data to/from storage. Access control functions, which determine who can access projects containing that data, are also important test items.

Therefore, we classified the main test perspectives as follows:

- Access subject ... Specifies who accesses the data. Defines types such as project owners, read-only members, and read-write members.
- Access method ... Specifies storage service types and their authentication information, as well as access methods such as via API or web UI.
- Operation ... Specifies functions to be tested, such as data registration, retrieval, and deletion for storage.

The basic policy is to define tests for operations, with access subjects and access methods provided as parameters. For example, instead of separating test items like "file operations by owner" and "file operations by non-owner," we parameterize test items as "file operations (access subject, check items)" to minimize their types and improve maintainability.

Examples of parameterization include:

- File upload/download test (storage type, access subject (owner/non-owner with write permission))

Operations may depend on each other. For example, "file upload/download test (standard storage)" can be executed independently, but when testing external storage like Amazon S3, storage authentication information must be registered beforehand. However, since the method of setting authentication information differs for each storage service type, these are treated as separate operations. For example, the configuration for Amazon S3 testing consists of two operations:

- Amazon S3 authentication information registration/deletion test
  - File upload/download test (Amazon S3)

The file upload/download test needs to be executed after Amazon S3 authentication information is registered. Also, after the file upload/download test, the test to delete Amazon S3 authentication information needs to be executed. Therefore, we design it so that the file upload/download test is called from the Amazon S3 authentication information registration/deletion test. Which test to call is realized by specifying the Jupyter Notebook name to call using papermill's parameter specification function. This allows flexible management of test execution order and dependencies.

Test items that don't depend on each other are designed to be executed independently and in parallel. Considerations for enabling parallel execution include:

- Allocating resources (projects, storage, etc.) used in tests for each test
- Releasing allocated resources after test completion

If projects or storage are shared between tests, test results may change depending on the test execution order.
These considerations help avoid test environment conflicts and maintain test independence.

## Jupyter Notebook Management

Integration tests are realized through automatic execution of Jupyter Notebooks. Jupyter Notebooks are broadly classified into the following two categories:

1. Test procedure Jupyter Notebooks - Example: `テスト手順-ストレージ共通.ipynb`
2. Integration test execution/summary Jupyter Notebooks - Example: `結合試験-実行.ipynb`

Test procedure Jupyter Notebooks contain test procedures for regular monitoring. They contain code for headless browser operations using Playwright https://playwright.dev/.
These Notebooks save video captures and HAR files recording communication content, and in case of error termination, the last capture image, to a designated directory upon completion.
Integration test execution/summary Jupyter Notebooks execute test procedure Jupyter Notebooks and compile the results.
These Notebooks execute test procedure Notebooks, summarize their results, and save them as evidence in files.

When adding new Jupyter Notebooks, start the filename with "テスト手順-" or "取りまとめ-" to indicate which type it is. `結合試験-実行.ipynb` is an exception to this rule. `結合試験-実行.ipynb` uses this filename structure when collecting results and compiling them into summaries.

### Test Procedure Jupyter Notebooks

Test procedure Jupyter Notebooks have the following structure:

1. Parameter settings
2. Test procedure description

Parameter settings are described in cells with the `parameters` tag according to papermill conventions.
In `テスト手順-一般ユーザーログイン〜ファイル操作-定点監視用.ipynb`, the following is written in the first cell:

```python
rdm_url = 'https://rdm.nii.ac.jp/'
idp_name = 'GakuNin RDM IdP'
idp_username = None
idp_password = None
default_result_path = None
project_name = 'テスト用プロジェクト'
close_on_fail = False
```

These variables control connection destination URLs, login information, result save locations, project names, and behavior on error occurrence.
As shown above, many of these are empty, but values are overwritten by papermill from the calling test execution/summary Jupyter Notebook.

For cases where test procedure Jupyter Notebooks are created manually rather than from papermill, some settings prompt for user input when values are empty.

```python
if idp_username is None:
    idp_username = input(prompt=f'Username for {idp_name}')
if idp_password is None:
    idp_password = getpass(prompt=f'Password for {idp_username}@{idp_name}')
(len(idp_username), len(idp_password))
```

The above code prompts users for input when `idp_username` and `idp_password` are empty.
During command-line execution with papermill, such input-prompting code cannot be executed. Therefore, values for these variables must be specified from papermill.

Test procedure descriptions contain code for browser operations using Playwright APIs.
Utility scripts are provided for attaching capture images to output results during cell execution and obtaining necessary information when errors occur.
These are stored in the `scripts/` directory.

When using the utility script `scripts/playwright.py`, initialize as follows:

```python
import importlib
import pandas as pd

import scripts.playwright
importlib.reload(scripts.playwright)

from scripts.playwright import *
from scripts import grdm

await init_pw_context(close_on_fail=close_on_fail, last_path=default_result_path)
```

This code initializes Playwright and sets the result save location and behavior on error occurrence.
Setting `close_on_fail` to `True` discards all related resources on error and saves video captures and HAR files.
Setting it to `False` only takes screen captures while maintaining resources.
When creating Jupyter Notebooks, setting `close_on_fail` to `False` allows continued operations.
During automatic execution with papermill, setting it to `True` releases resources on error and retrieves related data such as video captures and HAR files.

`default_result_path` specifies the result save location. If `None`, it saves to `~/last-screenshots`.

Test procedures are described in the following format:

```python
async def _step(page):
    await page.goto(rdm_url)

    # Click "同意する" (Agree)
    await page.locator('//button[text() = "同意する"]').click()

    # Confirm "同意する" is no longer displayed
    await expect(page.locator('//button[text() = "同意する"]')).to_have_count(0, timeout=500)

await run_pw(_step)
```

Using the `run_pw` function allows executing specified procedures.
`run_pw` is a function provided by the utility script that initializes the Playwright context and executes specified procedures.
Upon completion, it returns a screen capture as a return value, allowing you to check the screen state.

The function `_step` given to `run_pw` takes Playwright's `page` object as an argument and performs browser operations within it.
This function broadly performs the following operations:

1. Page operations
2. State confirmation after operations

Page operations are performed using Playwright's API. For example, you can navigate to a specified URL with `page.goto`, and execute a click by calling `click` on an element specified with `page.locator`.
Browser operations can be automated using APIs described at https://playwright.dev/python/docs/pages.

Post-operation state confirmation is performed using the `expect` function. The `expect` function waits until specified conditions are met, then proceeds to the next process.
Page element states can be confirmed using APIs described at https://playwright.dev/python/docs/test-assertions.
If conditions are not met within the time specified by `timeout`, an error occurs.

#### Structure and Details of Test Procedure Description

The test procedure description section typically consists of cells arranged as follows:

1. Markdown cell with Level 1 heading in the first line
2. Markdown cell with Level 2 heading in the second line
3. Cell defining `_step` function and executing it with utility `run_pw`
4. (Alternating between 2 and 3)
5. Cleanup processing

In practice, you may arrange multiple groups of 1 through 4.
We call this group a StepSequence, and 1 a StepSequence Header. Similarly, we call a group of 2 and 3 a Step, and 2 a Step Header. Multiple cells may be placed in 3. For example, the initialization cell with `init_pw_context` mentioned above is an example.

It's recommended to include the following content from the second line onward in the StepSequence Header:

`- Subsystem name: {}`

`- Page/Add-on: {}`

`- Function category: {}`

`- Scenario name: {}`

`- Test data to prepare: {}`

Where `{}` is a placeholder, describe content appropriate to that StepSequence. Including the heading content, these are reflected in the xlsx file summarizing test results, so describing them appropriately is expected to make results easier to understand.

The Step Header heading content and content from the second line onward are also reflected in the xlsx file, so describing the Step explanation from the second line onward as needed helps understanding.

For both StepSequence Headers and Step Headers, please use `#` notation for the first-line heading.

Calling `run_pw` more than once in a single Step is not recommended. While formally allowed, only the last screenshot generated in that Step is saved to the result directory by `run_pw`.

#### Element Identification

When identifying elements as operation targets, use `page.locator()`. `page.locator()` can identify elements using CSS selectors or XPath. We recommend the following descriptions for selectors to identify elements:

- Specify id attribute ... Since id attributes specified for elements are in principle unique, you can write descriptions resistant to GUI changes.
- Specify data-test attribute ... Some GUIs created in GRDM have `data-test` attributes added to elements, explicitly indicating they are attributes for identifying elements from test code.
- Specify text ... You can specify text displayed on buttons. With this method, many modifications may be needed when multilingual support is required.
- Specify by combining multiple elements ... If the target element doesn't have the above attributes, you can identify it by combining multiple elements. For example, specifying specific text adjacent to a folder icon.

For examples of XPath and CSS selectors, refer to Jupyter Notebooks.
When existing GUI changes occur, these descriptions may need modification. If errors such as "element not found" occur, refer to the previous screenshot, identify the screen, use the browser's developer tools to identify the element, and modify the selector.

Note that while you can check using browser developer tools, XPath like `//*[@id="tb-tbody"]/div/div/div[11]/div[1]/span[2]/span` includes element hierarchy and order internally, requiring modifications to follow GUI changes, so it's not recommended.

#### Utility Functions

GRDM provides utility function groups for common GUI operations. They are defined in scripts/grdm.py.

- expect_idp_login ... Waits until IdP login is possible. Waits until the ID/PW input form is displayed.
- login_idp ... Logs into IdP. Enters ID/PW to log in.
- ensure_project_exists ... Creates a project if one with the specified name doesn't exist.
- delete_project ... Deletes the specified project.
- get_select_storage_title_locator, get_select_storage_title_xpath ... Functions for identifying elements showing storage names like "NII Storage".
- get_select_expanded_storage_title_locator, get_select_expanded_storage_title_xpath ... Functions for identifying elements showing expanded storage names. Used when waiting for storage content to load.
- get_select_folder_title_locator, get_select_folder_title_xpath, get_select_folder_toggle_locator, get_select_folder_toggle_xpath ... Functions for identifying elements showing folder names. title identifies folder name text, toggle identifies folder expand/collapse icon elements.
- get_select_file_title_locator, get_select_file_title_xpath ... Functions for identifying elements showing file names.
- get_select_file_extension_locator, get_select_file_extension_xpath ... Functions for identifying icon elements showing file types.
- wait_for_uploaded ... Function for waiting until files are uploaded. Waits while file progress bars are displayed.
- upload_file, drop_file ... Functions for uploading files. upload_file uses the "Upload" button that appears when selecting storage or folders, drop_file uploads by dropping files onto the screen. Since drop_file converts files to JavaScript for execution, it's only usable for files up to a few MB.

### Integration Test Execution/Summary Jupyter Notebooks

Integration test execution/summary Jupyter Notebooks have the following structure:

1. Parameter settings
2. Test procedure Jupyter Notebook execution
3. Result compilation

In the first **Parameter settings**, variables necessary for executing the target integration test are set. This information is used as arguments passed to executed Notebooks. For example, system URLs and user authentication information are included.
Next, in **Test procedure Jupyter Notebook execution**, papermill is used to execute specified test procedure Jupyter Notebooks with parameters. At this stage, test Notebooks are processed and results for each step are generated. Depending on test configuration, executed Notebooks may call other Notebooks.
In **Result compilation**, after test execution, obtained results are collected and compiled. This compilation includes summaries of failures if any, and visualization of performance information.

Video screen captures are attached to all test procedure Jupyter Notebook execution results to help confirm situations. Subtitle strings showing headings of cells being executed are inserted as references for which test procedures correspond to video scenes.

## Security and Sensitive Information Management

When managing and publishing this repository with Git, set up pre-commit hooks to prevent leakage of sensitive information.

### Setup Instructions

1. **Install required tools**
   ```bash
   # For macOS
   brew install gitleaks
   
   # Install pre-commit
   pip install pre-commit
   ```

2. **Enable pre-commit hooks**
   ```bash
   # Execute in repository root directory
   pre-commit install
   ```

3. **Verify operation**
   ```bash
   # Check all files
   pre-commit run --all-files
   ```

### Detected Sensitive Information

Pre-commit hooks automatically detect the following information and block commits:
- AWS access keys, secret keys
- API tokens, authentication tokens
- Private keys
- Other sensitive information patterns

Additionally, unnecessary metadata (lc_server_signature.history) is automatically removed when committing Notebook files.

### Cleaning Notebook Output

Jupyter Notebook output cells may record runtime information. Clear cell outputs as needed.