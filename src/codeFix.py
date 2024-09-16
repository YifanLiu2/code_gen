import os, json, argparse
from tqdm import tqdm
from src.codeGenerator import PROMPT_TYPE, CodeGenerator
from src.llm import GPTChat
import random


SELF = "Self"
USAGE = "Usage"
FAILURE = "FAILURE"
LINE = "Line"
REASON = "Reason"
HINT = "Hint"
CLARIFICATION = "Clarification"

# with open("data/curated_data/examples.json") as f:
#     EXAMPLE = json.load(f)

# with open("data/data3/data3_failure_examples.json") as f:
#     FAILURE_EXAMPLE = json.load(f)

FIX_TYPE = [LINE, REASON, HINT]

PROMPT = """
The previously generated code is incorrect.

{fix}

Analyze the reason and revise the code based on the provided information, following all previous instructions and format.
"""

def load_prompts(fix_prompt_path: str) -> dict:
    """
    Load the fix type prompts and fix prompts from JSON files.

    fix_template (str): Path to the JSON file containing fix type prompts.
    fix_prompt (str): Path to the JSON file containing fix prompts.
    """
    with open(fix_prompt_path, "r") as fix_file:
        fix_prompts = json.load(fix_file)
    return fix_prompts


def write_output(output_dir_for_type: str, task_id: str, solution: str, new_message: list) -> None:
    """
    Write the generated solution and message to output files.

    output_dir_for_type (str): Directory where the output files will be saved.
    task_id (str): The task ID associated with the message.
    solution (str): The generated solution.
    new_message (list): A list represent new messages generated by the code generator.
    fix_type (str): The type of fix applied.
    """
    solutions_path = os.path.join(output_dir_for_type, "solutions.jsonl")
    messages_path = os.path.join(output_dir_for_type, "messages.jsonl")

    with open(solutions_path, 'a') as file_s, open(messages_path, 'a') as file_m:
        file_s.write(json.dumps({"task_id": task_id, "completion": solution}) + '\n')
        file_m.write(json.dumps({"task_id": task_id, "message": new_message}) + '\n')

def clear_output_files(output_dir: str):
    """
    Clear the contents of the output files.

    output_dir (str): Directory where the output files will be saved.
    """
    if os.path.exists(output_dir):
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                with open(file_path, 'w') as f:
                    f.truncate()

def exp_example(generator: CodeGenerator, fix_prompts: dict, message_json: dict, output_dir: str):
    task_id = message_json["task_id"]
    message = message_json["message"]

    examples = EXAMPLE.get(task_id, [])

    for num_exp in tqdm(range(10), desc=f"Experiment: {task_id}"):
        num_exp = min(num_exp, len(examples))
        sample_examples = random.sample(examples, num_exp)
        sample_str = "\n".join(sample_examples)
        prompt = f"Example correct usage:\n{sample_str}"

        try:
            # generate fix
            solution, new_message = generator.generate_code(prompt=PROMPT.format(fix=prompt), message=message)    
            output_dir_for_type = os.path.join(output_dir, f"{USAGE.lower()}_{num_exp}")
            
            # save results
            os.makedirs(output_dir_for_type, exist_ok=True)
            write_output(output_dir_for_type, task_id, solution, new_message)
        
        except Exception as e:
            print(f"Error fixing {task_id}: {e}")
            continue 


def exp_failure(generator: CodeGenerator, fix_prompts: dict, message_json: dict, output_dir: str):
    task_id = message_json["task_id"]
    message = message_json["message"]

    examples = FAILURE_EXAMPLE.get(task_id, [])

    for i in tqdm(range(5), desc=f"Experiment: {task_id}"):
        num_exp = min(i, len(examples))
        sample_examples = random.sample(examples, num_exp)
        sample_str = "\n".join(sample_examples)
        prompt = f"Incorrect usage:\n{sample_str}"

        try:
            # generate fix
            solution, new_message = generator.generate_code(prompt=PROMPT.format(fix=prompt), message=message)  
            output_dir_for_type = os.path.join(output_dir, f"{FAILURE.lower()}_{i}")
            print(output_dir_for_type)
            
            # save results
            os.makedirs(output_dir_for_type, exist_ok=True)
            write_output(output_dir_for_type, task_id, solution, new_message)
        
        except Exception as e:
            print(f"Error fixing {task_id}: {e}")
            continue 


def exp_base(generator: CodeGenerator, message_json: dict, output_dir: str):
    task_id = message_json["task_id"]
    message = message_json["message"]

    try:
        # generate fix
        solution, new_message = generator.generate_code(prompt=PROMPT.format(fix=""), message=message)    
        output_dir_for_type = os.path.join(output_dir, f"{SELF.lower()}")
        
        # save results
        os.makedirs(output_dir_for_type, exist_ok=True)
        write_output(output_dir_for_type, task_id, solution, new_message)
    
    except Exception as e:
        print(f"Error fixing {task_id}: {e}")


def exp_prompt(generator: CodeGenerator, fix_prompts: dict, message_json: dict, output_dir: str):
    task_id = message_json["task_id"]
    message = message_json["message"]

    fix_prompts_for_task = fix_prompts.get(task_id, {})

    if fix_prompts_for_task:
        clarification = fix_prompts_for_task.get(CLARIFICATION, None)
        if clarification is not None:
            prompt = f"Clarification on the previous instruction\n{clarification}"

            try:
                # generate fix
                solution, new_message = generator.generate_code(prompt=PROMPT.format(fix=prompt), message=message)    
                output_dir_for_type = os.path.join(output_dir, f"{CLARIFICATION.lower()}")
                
                # save results
                os.makedirs(output_dir_for_type, exist_ok=True)
                write_output(output_dir_for_type, task_id, solution, new_message)
            
            except Exception as e:
                print(f"Error fixing {task_id}: {e}")


def exp_generate(generator: CodeGenerator, fix_prompts: dict, message_json: dict, output_dir: str):
    task_id = message_json["task_id"]
    message = message_json["message"]

    fix_prompts_for_task = fix_prompts.get(task_id, {})

    if fix_prompts_for_task:
        line = fix_prompts_for_task.get(LINE, None)
        reason = fix_prompts_for_task.get(REASON, None)
        hint = fix_prompts_for_task.get(HINT, None)

        prompts = {}
        if line is not None:
            prompts["line"] = f"Incorrect line:\n{line}"
        
        if reason is not None:
            prompts["reason"] = f"Incorrect reason:\n{reason}"
        
        if hint is not None:
            prompts["hint"] = f"Implementation hint:\n{hint}"

        if line is not None and reason is not None:
            prompts["line_reason"] = prompts["line"] + '\n\n' + prompts["reason"]

        if line is not None and hint is not None:
            prompts["line_hint"] = prompts["line"] + '\n\n' + prompts["hint"]

        if reason is not None and hint is not None:
            prompts["reason_hint"] = prompts["reason"] + '\n\n' + prompts["hint"]
        
        if line is not None and reason is not None and hint is not None:
            prompts["line_reason_hint"] = prompts["line"] + '\n\n' +prompts["reason"] + '\n\n' + prompts["hint"]

        for fix_type, prompt in tqdm(prompts.items(), desc=f"Processing task {task_id} ..."):
            try:   
                # generate fix
                solution, new_message = generator.generate_code(prompt=PROMPT.format(fix=prompt), message=message)    
                output_dir_for_type = os.path.join(output_dir, fix_type)
                
                # save results
                os.makedirs(output_dir_for_type, exist_ok=True)
                write_output(output_dir_for_type, task_id, solution, new_message)
            
            except Exception as e:
                print(f"Error fixing {task_id} for fix type {fix_type}: {e}")
                continue 


def fix_codes(generator: CodeGenerator, code_dir: str, failed_path: str, fix_prompt_path: str, output_dir: str, clear: bool = False) -> None:
    """
    Fix codes by generating new solutions and messages based on fix prompts.

    generator (CodeGenerator): An instance of the code generator.
    code_dir (str): Directory containing the code and messages.
    failed_path (str): Path to the JSON file containing failed task for each prompt type.
    fix_template_path (str): Path to the JSON file containing fix template.
    fix_prompt_path (str): Path to the JSON file containing fix prompts.
    output_dir (str): Directory where the output files will be saved.
    """
    # clear output content
    if clear:
        clear_output_files(output_dir=output_dir)
    with open(failed_path, "r") as f:
        failed = json.load(f)

    # load fix prompts
    try:
        fix_prompts = load_prompts(fix_prompt_path)
    except Exception as e:
        print(f"Failed to load prompts: {e}")
        return
    
    # process for each prompt type
    messages_path = os.path.join(code_dir, "messages.jsonl")
    if not os.path.exists(messages_path):
        print(f"Code generation not detected.")
        return
    
    dataset_name = os.path.basename(code_dir)
    failed_list = failed.get(dataset_name, []) # define failed task
    with open(messages_path, "r") as f:
        # process for each task_id
        lines = f.readlines()
        lines = [json.loads(line) for line in lines]
        lines = [line for line in lines if line["task_id"] in failed_list]
    
    for message_json in tqdm(lines, desc=f"Processing tasks in {code_dir}", leave=False):
            # exp_base(generator=generator, message_json=message_json, output_dir=output_dir)
            # exp_example(generator=generator, fix_prompts=fix_prompts, message_json=message_json, output_dir=output_dir)
            # exp_generate(generator=generator, fix_prompts=fix_prompts, message_json=message_json, output_dir=output_dir)
            # exp_failure(generator=generator, fix_prompts=fix_prompts, message_json=message_json, output_dir=output_dir)
            exp_prompt(generator=generator, fix_prompts=fix_prompts, message_json=message_json, output_dir=output_dir)






########################### Prompt Type ###############################



def main(args):
    agent = GPTChat()
    generator = CodeGenerator(agent=agent)

    code_dir = args.code_dir
    failed_path = args.failed_path
    fix_prompt_path = args.fix_prompt_path
    output_dir = args.output_dir

    if not os.path.exists(code_dir):
        raise ValueError(f"Invalid code directory: {code_dir}")
    
    if not os.path.exists(failed_path) or not failed_path.endswith(".json"):
        raise ValueError(f"Invalid path for failed tasks, must be a .json file: {failed_path}")
    
    if not os.path.exists(fix_prompt_path) or not fix_prompt_path.endswith(".json"):
        raise ValueError(f"Invalid path for fix prompts, must be a .json file: {fix_prompt_path}")
    
    fix_codes(generator, code_dir=code_dir, fix_prompt_path=fix_prompt_path, output_dir=output_dir, failed_path=failed_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix codes by generating new solutions and messages based on fix prompts.")
    parser.add_argument('--code_dir', type=str,help='Directory containing the code and messages.')
    parser.add_argument('--failed_path', type=str, default="data/curated_data/failed.json", help='Path to the JSON file containing failed task for each prompt type')
    parser.add_argument('--fix_prompt_path', type=str, default="data/curated_data/fix_prompts.json", help='Path to the JSON file containing fix prompts.')
    parser.add_argument('--output_dir', type=str, default="data/fix", help='Directory where the output files will be saved.')

    args = parser.parse_args()

    main(args)