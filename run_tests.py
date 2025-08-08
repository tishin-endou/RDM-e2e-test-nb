#!/usr/bin/env python3
"""
Automated test runner for GRDM integration tests.
Based on 結合試験-実行.ipynb but runs only automated tests (run_notebook).
Manual tests (run_manual_notebook) are skipped.
"""

import os
import sys
import yaml
import argparse
import tempfile
import traceback
import subprocess
import shutil
from datetime import datetime
import papermill as pm
import nbformat


class TestRunner:
    def __init__(self, config_path, show_disk_usage=False, failed_result_path=None):
        self.config_path = config_path
        self.config = None
        self.work_dir = tempfile.mkdtemp()
        self.result_dir = None
        self.result_notebooks = []
        self.local_vars = {}
        self.show_disk_usage = show_disk_usage
        self.failed_result_path = failed_result_path
        
        # Default configuration values
        self.rdm_url = 'https://rdm.example.com/'
        self.admin_rdm_url = 'https://admin.rdm.example.com/'
        self.rdm_project_url_1 = 'https://rdm.example.com/tvuxd/'
        self.rdm_project_name_1 = 'test_login'
        self.rdm_project_url_2 = 'https://rdm.example.com/xwz59/'
        
        # Default test settings
        self.skip_failed_test = True
        self.transition_timeout = 60000
        self.skip_preview_check = False
        self.skip_default_storage = False
        self.skip_metadata = False
        self.skip_admin = False
        self.enable_1gb_file_upload = False
        self.skip_erad_completion_test = False
        
        # Storage configurations
        self.storages_oauth = [
            {'id': 'dropbox', 'name': 'Dropbox'},
            {'id': 'googledrive', 'name': 'Google Drive'},
            {'id': 'onedrive', 'name': 'OneDrive'},
            {'id': 'nextcloud', 'name': 'Nextcloud'},
        ]
        
        self.storages_s3 = [
            {'id': 's3', 'name': 'Amazon S3'},
            {'id': 's3compat', 'name': 'S3 Compatible Storage'},
        ]
        
    def load_config(self):
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            print(f'Configuration file {self.config_path} not found.')
            sys.exit(1)
            
        with open(self.config_path) as f:
            self.config = yaml.load(f.read(), yaml.SafeLoader)
            
        # Load configuration values
        for key, value in self.config.items():
            setattr(self, key, value)
            
        # Validate required parameters
        required_params = [
            'idp_username_1', 'idp_password_1',
            'idp_username_2', 'idp_password_2',
        ]
        
        for param in required_params:
            if not hasattr(self, param) or getattr(self, param) is None:
                print(f'Error: Required parameter {param} is not set in configuration.')
                sys.exit(1)
                
    def make_result_dir(self):
        """Create result directory with timestamp."""
        run_id = datetime.now().strftime('%Y%m%d-%H%M%S')
        self.result_dir = f'result/result-{run_id}'
        os.makedirs(self.result_dir)
        return self.result_dir
        
    def run_notebook(self, base_notebook, optional_result_id=None, **optional_params):
        """Execute a notebook using papermill."""
        _, filename = os.path.split(base_notebook)
        result_id, _ = os.path.splitext(filename)
        if optional_result_id:
            result_id += optional_result_id
            
        result_notebook = os.path.join(self.result_dir, result_id + '.ipynb')
        result_path = os.path.join(self.result_dir, result_id)
        os.makedirs(result_path, exist_ok=True)
        
        # Base parameters
        params = dict(
            rdm_url=self.rdm_url,
            idp_name=getattr(self, 'idp_name_1', None),
            idp_username=getattr(self, 'idp_username_1', None),
            idp_password=getattr(self, 'idp_password_1', None),
            idp_name_1=getattr(self, 'idp_name_1', None),
            idp_username_1=getattr(self, 'idp_username_1', None),
            idp_password_1=getattr(self, 'idp_password_1', None),
            default_result_path=result_path,
            close_on_fail=True,
            transition_timeout=self.transition_timeout,
        )
        params.update(optional_params)
        
        print(f'Running notebook: {base_notebook}')
        print(f'  Result: {result_notebook}')
        
        # Show disk usage before test if enabled
        if self.show_disk_usage:
            subprocess.run(['df', '-h'])
        
        try:
            pm.execute_notebook(
                base_notebook,
                result_notebook,
                parameters=params
            )
            print(f'  Status: SUCCESS')
        except pm.PapermillExecutionError:
            if not self.skip_failed_test:
                raise
            print(f'  Status: FAILED (continuing)')
            traceback.print_exc()
        
        # Show disk usage after test if enabled
        if self.show_disk_usage:
            subprocess.run(['df', '-h'])
            
        return result_notebook
        
    def run_login_tests(self):
        """Run login-related tests."""
        print('\n=== Login Tests ===')
        
        if hasattr(self, 'idp_name_1') and self.idp_name_1:
            self.result_notebooks.append(
                self.run_notebook(
                    'テスト手順-未ログイン.ipynb',
                    rdm_project_url_1=self.rdm_project_url_1,
                    rdm_project_url_2=self.rdm_project_url_2,
                )
            )
            
            self.result_notebooks.append(
                self.run_notebook(
                    'テスト手順-ログイン.ipynb',
                    rdm_project_url_1=self.rdm_project_url_1,
                    rdm_project_name_1=self.rdm_project_name_1,
                    rdm_project_url_2=self.rdm_project_url_2,
                )
            )
        else:
            print('Skipping login tests (IdP not configured)')
            
    def run_storage_tests(self):
        """Run storage-related tests."""
        print('\n=== Storage Tests ===')
        
        # Default storage test
        if not self.skip_default_storage:
            self.result_notebooks.append(
                self.run_notebook(
                    '取りまとめ-NIIストレージ.ipynb',
                    enable_1gb_file_upload=self.enable_1gb_file_upload,
                    skip_failed_test=self.skip_failed_test,
                    skip_preview_check=self.skip_preview_check,
                    too_large_file_upload_size=None,  # Disable large file test
                )
            )
            
        # S3 storage tests
        rdm_project_prefixes = {}
        for storage_info in self.storages_s3:
            storage_id = storage_info['id']
            storage_name = storage_info['name']
            
            # Check if S3 credentials are configured
            access_key_1 = getattr(self, f'{storage_id}_access_key_1', None)
            if not access_key_1:
                print(f'Skipping {storage_name} (credentials not configured)')
                continue
                
            print(f'\nS3 storage test - {storage_name}')
            rdm_project_prefixes[storage_id] = 'TEST-{}-{}'.format(
                storage_id.upper(), 
                datetime.now().strftime('%Y%m%d-%H%M%S')
            )
            
            self.result_notebooks.append(
                self.run_notebook(
                    '取りまとめ-S3共通.ipynb',
                    optional_result_id=f'-{storage_name}',
                    s3_access_key_1=getattr(self, f'{storage_id}_access_key_1', None),
                    s3_secret_access_key_1=getattr(self, f'{storage_id}_secret_access_key_1', None),
                    s3_default_region_1=getattr(self, f'{storage_id}_default_region_1', None),
                    s3_test_bucket_name_1=getattr(self, f'{storage_id}_test_bucket_name_1', None),
                    s3_access_key_2=getattr(self, f'{storage_id}_access_key_2', None),
                    s3_secret_access_key_2=getattr(self, f'{storage_id}_secret_access_key_2', None),
                    s3_default_region_2=getattr(self, f'{storage_id}_default_region_2', None),
                    s3_test_bucket_name_2=getattr(self, f'{storage_id}_test_bucket_name_2', None),
                    rdm_project_prefix=rdm_project_prefixes[storage_id],
                    target_storage_name=storage_name,
                    target_storage_id=storage_id,
                    enable_1gb_file_upload=self.enable_1gb_file_upload,
                    skip_failed_test=self.skip_failed_test,
                    skip_preview_check=self.skip_preview_check,
                    s3compat_type_name_1=getattr(self, 's3compat_type_name_1', None) if storage_id == 's3compat' else None,
                    s3compat_type_name_2=getattr(self, 's3compat_type_name_2', None) if storage_id == 's3compat' else None,
                    skip_too_many_files_check=storage_info.get('skip_too_many_files_check', False),
                )
            )
            
        # OAuth storage tests (require manual setup, so skip in automated tests)
        print('\nSkipping OAuth storage tests (require manual setup)')
        
    def run_metadata_tests(self):
        """Run metadata addon tests."""
        print('\n=== Metadata Tests ===')
        
        if not self.skip_metadata:
            self.result_notebooks.append(
                self.run_notebook(
                    '取りまとめ-Metadataアドオン.ipynb',
                    idp_name_2=getattr(self, 'idp_name_2', None),
                    idp_username_2=getattr(self, 'idp_username_2', None),
                    idp_password_2=getattr(self, 'idp_password_2', None),
                    skip_failed_test=self.skip_failed_test,
                    skip_erad_completion_test=self.skip_erad_completion_test,
                )
            )
            
    def run_admin_tests(self):
        """Run administrator function tests."""
        print('\n=== Admin Tests ===')
        
        if not self.skip_admin:
            self.result_notebooks.append(
                self.run_notebook(
                    '取りまとめ-管理者機能.ipynb',
                    admin_rdm_url=self.admin_rdm_url,
                    idp_name_2=getattr(self, 'idp_name_2', None),
                    idp_username_2=getattr(self, 'idp_username_2', None),
                    idp_password_2=getattr(self, 'idp_password_2', None),
                    skip_failed_test=self.skip_failed_test,
                    search_node_id=getattr(self, 'admin_search_node_id', None),
                    search_node_title=getattr(self, 'admin_search_node_title', None),
                    search_user_name=getattr(self, 'admin_search_user_name', None),
                    search_user_by_id=getattr(self, 'admin_search_user_by_id', None),
                    search_user_by_name=getattr(self, 'admin_search_user_by_name', None),
                    search_user_by_email=getattr(self, 'admin_search_user_by_email', None),
                    search_registration_id=getattr(self, 'admin_search_registration_id', None),
                    search_registration_title=getattr(self, 'admin_search_registration_title', None),
                    announcement_title=getattr(self, 'admin_announcement_title', None),
                    announcement_body=getattr(self, 'admin_announcement_body', None),
                    target_organization=getattr(self, 'admin_target_organization', None),
                    timestamp_project_name=getattr(self, 'admin_timestamp_project_name', None),
                    timestamp_start_date=getattr(self, 'admin_timestamp_start_date', None),
                    timestamp_end_date=getattr(self, 'admin_timestamp_end_date', None),
                    timestamp_user=getattr(self, 'admin_timestamp_user', None),
                    quota_user_id=getattr(self, 'admin_quota_user_id', None),
                    entitlement_text=getattr(self, 'admin_entitlement_text', None),
                )
            )
            
    def check_notebook_errors(self, notebook_path):
        """Check a notebook and all its sub-notebooks recursively for execution errors."""
        all_errors = []
        
        # Check the notebook itself
        with open(notebook_path, 'r') as f:
            nb = nbformat.read(f, as_version=nbformat.NO_CONVERT)
        
        for i, cell in enumerate(nb.cells):
            if cell.cell_type != 'code' or 'outputs' not in cell:
                continue
                
            for output in cell.outputs:
                if output.get('output_type') != 'error':
                    continue
                    
                all_errors.append({
                    'notebook': notebook_path,
                    'cell': i,
                    'ename': output.get('ename', 'Unknown'),
                    'evalue': output.get('evalue', 'Unknown error'),
                    'traceback': output.get('traceback', [])
                })
        
        # Check notebooks/ subdirectory recursively
        base_path = os.path.splitext(notebook_path)[0]
        notebooks_dir = os.path.join(base_path, 'notebooks')
        
        if not os.path.exists(notebooks_dir) or not os.path.isdir(notebooks_dir):
            return all_errors
        
        for sub_notebook in os.listdir(notebooks_dir):
            if not sub_notebook.endswith('.ipynb'):
                continue
                
            sub_notebook_path = os.path.join(notebooks_dir, sub_notebook)
            # Recursively check this sub-notebook and its children
            all_errors.extend(self.check_notebook_errors(sub_notebook_path))
        
        return all_errors
    
    def extract_failed_notebooks(self):
        """Extract and copy failed notebooks to a separate directory."""
        if self.failed_result_path is None:
            return 0
        
        os.makedirs(self.failed_result_path, exist_ok=True)
        
        failed_count = 0
        
        # Check all executed notebooks
        for notebook_path in self.result_notebooks:
            # Check notebook for errors
            notebook_errors = self.check_notebook_errors(notebook_path)
            
            if notebook_errors:
                # Get the base path without extension
                base_path = os.path.splitext(notebook_path)[0]
                notebook_name = os.path.basename(notebook_path)
                
                # Copy the notebook file
                rel_path = os.path.relpath(notebook_path, os.path.dirname(self.result_dir))
                dest_path = os.path.join(self.failed_result_path, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(notebook_path, dest_path)
                print(f'  Copied failed notebook: {notebook_name}')
                
                # Copy the associated directory if it exists
                if os.path.exists(base_path) and os.path.isdir(base_path):
                    rel_dir_path = os.path.relpath(base_path, os.path.dirname(self.result_dir))
                    dest_dir_path = os.path.join(self.failed_result_path, rel_dir_path)
                    shutil.copytree(base_path, dest_dir_path, dirs_exist_ok=True)
                    print(f'  Copied associated directory: {os.path.basename(base_path)}/')
                
                failed_count += 1
        
        if failed_count > 0:
            print(f'\nExtracted {failed_count} failed notebook(s) to: {self.failed_result_path}')
        else:
            print('\nNo failed notebooks found')
        
        return failed_count
    
    def run_all_tests(self):
        """Run all configured tests."""
        print(f'Starting test run at {datetime.now()}')
        print(f'Configuration: {self.config_path}')
        print(f'Result directory: {self.result_dir}')
        
        self.run_login_tests()
        self.run_storage_tests()
        self.run_metadata_tests()
        self.run_admin_tests()
        
        print(f'\nTest run completed at {datetime.now()}')
        print(f'Total notebooks executed: {len(self.result_notebooks)}')
        print(f'Results saved to: {self.result_dir}')
        
        # Extract failed notebooks for easier debugging
        self.extract_failed_notebooks()
        
        # Check for errors in executed notebooks
        if self.skip_failed_test:
            all_errors = []
            
            for notebook_path in self.result_notebooks:
                # Check notebook and all its sub-notebooks for errors
                notebook_errors = self.check_notebook_errors(notebook_path)
                if notebook_errors:
                    all_errors.extend(notebook_errors)
            
            if all_errors:
                # Group errors by notebook
                notebooks_with_errors = {}
                for error in all_errors:
                    notebook = error['notebook']
                    if notebook not in notebooks_with_errors:
                        notebooks_with_errors[notebook] = []
                    notebooks_with_errors[notebook].append(error)
                
                error_msg = f"\nERROR: {len(notebooks_with_errors)} notebook(s) failed with errors:\n"
                for notebook_path, errors in notebooks_with_errors.items():
                    # Show relative path from result directory
                    rel_path = os.path.relpath(notebook_path, os.path.dirname(self.result_dir))
                    error_msg += f"\n{rel_path}:\n"
                    for error in errors[:3]:  # Show first 3 errors per notebook
                        error_msg += f"  - Cell {error['cell']}: {error['ename']}: {error['evalue']}\n"
                    if len(errors) > 3:
                        error_msg += f"  ... and {len(errors) - 3} more error(s)\n"
                
                print(error_msg, file=sys.stderr)
                raise RuntimeError(f"{len(notebooks_with_errors)} notebook(s) failed")
        
        return self.result_notebooks


def main():
    parser = argparse.ArgumentParser(
        description='Run GRDM integration tests automatically'
    )
    parser.add_argument(
        'config',
        help='Path to configuration YAML file'
    )
    parser.add_argument(
        '--show-disk-usage',
        action='store_true',
        help='Show disk usage before and after each test'
    )
    parser.add_argument(
        '--failed-result-path',
        help='Path to directory where failed notebooks will be copied (if not specified, failed notebooks are not extracted)'
    )
    
    args = parser.parse_args()
    
    # Create and run tests
    runner = TestRunner(args.config, show_disk_usage=args.show_disk_usage, failed_result_path=args.failed_result_path)
    runner.load_config()
    runner.make_result_dir()
    
    try:
        runner.run_all_tests()
    except KeyboardInterrupt:
        print('\nTest run interrupted by user')
        sys.exit(1)
    except Exception as e:
        print(f'\nTest run failed with error: {e}')
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()