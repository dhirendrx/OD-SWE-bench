import argparse
import json
from context_manager import TestbedContextManager, TaskEnvContextManager
import os
from typing import Dict
from utils import DotDict
import os.path as osp

def is_json(myjson: str):
    try:
        json_object = json.loads(myjson)
    except ValueError as e:
        return False
    return True

def validate_args(args):
    if args.timeout is not None and args.timeout < 0:
        raise ValueError(f"Timeout must be a positive integer")

def verify_task_instances(data: Dict):
    """
    Sets up task environment context manager. Each task instance is then
    installed and validated within the context manager.
    Args:
        data: Dict containing task instances and other data
            task_instances: List of task instances
            + setup_testbed args
    """
    data_dict = DotDict(data)
    for task_instance in data_dict.task_instances:
        tcm = TaskEnvContextManager(
            task_instance,
            data_dict.testbed,
            data_dict.venv,
            data_dict.log_dir,
            data_dict.conda_path,
            verbose=data_dict.verbose,
            timeout=data_dict.timeout,
            log_suffix=data_dict.log_suffix,
        )
        tcm.__enter__()
        print("reset_task_env: ", tcm.reset_task_env(task_instance))
        print("run_install_task: ", tcm.run_install_task(task_instance))
        print("apply_test_patch: ", tcm.apply_patch(task_instance["test_patch"], patch_type="test"))
        tcm.__exit__()

def setup_testbed(data: Dict):
    """
    Creates testbed context manager and runs verify_task_instances in parallel
    Args:
        data: Dict containing task instances and other data
            task_instances: List of task instances
            log_dir: Path to log directory
            path_conda: Path to miniconda3 or anaconda installation
            testbed: Path to testbed directory
            temp_dir: Path to temporary directory for storing virtual envs
            timeout: Timeout (seconds) for testing script execution
            verbose: Verbose mode
    """
    data_dict = DotDict(data)
    tcm = TestbedContextManager(
        [data_dict.task_instances],
        data_dict.log_dir,
        path_conda=data_dict.conda_path,
        testbed=data_dict.testbed,
        temp_dir=data_dict.temp_dir,
        timeout=data_dict.timeout,
        verbose=data_dict.verbose,
    )
    tcm.__enter__()
    distributed_task_list = tcm.get_distributed_tasks()
    data_dict.func(distributed_task_list[0])
    tcm.__exit__()
    return

def main(args):
    devin_output = json.load(open(args.devin_output_path, "r"))
    devin_instance_ids = [_["instance_id"] for _ in devin_output]
    with open(args.instances_path, 'r', encoding='utf-8') as f:
        instances_list =  json.load(f)
    for item in instances_list:
        # if (args.instance_id != item["instance_id"]):
        #     continue
        if item["instance_id"] not in devin_instance_ids or \
            osp.exists(osp.join(args.log_dir, item["instance_id"] + ".log")):
            continue
        task_instance = item
        data_group = {
                "task_instances": task_instance,
                "func": verify_task_instances,
                **vars(args),
        }
        setup_testbed(data_group)
    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--instances_path", type=str, help="task instances path", required=True)
    # parser.add_argument("--instance_id", type=str, help="JSON String for an individual task instance", required=True)
    parser.add_argument("--log_dir", type=str, help="Path to log directory", required=True)
    parser.add_argument("--devin_output_path", type=str, help="Path to devin's output", required=True)
    parser.add_argument("--conda_path", type=str, help="(Optional) Path to miniconda3 or anaconda installation")
    parser.add_argument("--testbed", type=str, help="(Optional) Path to testbed directory")
    parser.add_argument("--venv", type=str, help="(Optional) Virtual environment for the test")
    parser.add_argument("--timeout", type=int, default=None, help="(Optional) Timeout (seconds) for testing script execution")
    parser.add_argument("--verbose", action="store_true", help="(Optional) Verbose mode")
    args = parser.parse_args()
    validate_args(args)
    main(args)