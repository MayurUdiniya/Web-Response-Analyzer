import os
import subprocess
import re
import hashlib

# Function to make multiple GET requests using curl and return the responses
def make_get_request_curl(url, num_requests=10):
    responses = []
    try:
        for _ in range(num_requests):
            response = subprocess.run(['curl', '-s', url], capture_output=True, text=True)
            responses.append(response)
        return responses
    except subprocess.CalledProcessError as e:
        return None

# Function to identify potential dynamic parameters by analyzing multiple responses
def identify_dynamic_parameters(responses):
    dynamic_params = set()
    for param_name in re.findall(r'(\w+)=([^&]+)', '&'.join([resp.stdout for resp in responses])):
        param_values = [match.group(1) for resp in responses for match in [re.search(fr'{param_name}=([^&]+)', resp.stdout)] if match]
        if len(set(param_values)) == len(param_values):
            dynamic_params.add(param_name)
    return dynamic_params

# Function to find a unique identifier in the original response that is not present in the example.com response
def find_unique_identifier(original_html, example_html, dynamic_params):
    for param in dynamic_params:
        original_html = re.sub(fr'{param}=([^&]+)', f'{param}=REDACTED', original_html)
        example_html = re.sub(fr'{param}=([^&]+)', f'{param}=REDACTED', example_html)

    original_words = set(re.findall(r'\b\w+\b', original_html))
    example_words = set(re.findall(r'\b\w+\b', example_html))
    unique_words = original_words.difference(example_words)
    if unique_words:
        unique_word = unique_words.pop()
        if unique_word != 'REDACTED':
            return unique_word
    return None

# Function to check for changes in response and return observed differences
def check_response_change(url, original_responses, dynamic_params):
    redirect_uri_match = re.search(r'redirect_uri=(https?://[^&]*)', url)
    if not redirect_uri_match:
        print(f"Failed to extract domain from redirect_uri: {url}")
        return None

    redirect_uri = redirect_uri_match.group(1)

    # First request: FUZZ the redirect_uri value with 'https://example.com'
    new_url_example = url.replace(redirect_uri, 'https://example.com')
    new_responses_example = make_get_request_curl(new_url_example)

    differences = {}
    if new_responses_example is not None:
        for i in range(len(original_responses)):
            if new_responses_example[i].stdout != original_responses[i].stdout:
                differences['html_diff'] = True

                # Find the unique identifier in the original response
                original_html = original_responses[i].stdout
                example_html = new_responses_example[i].stdout
                unique_word = find_unique_identifier(original_html, example_html, dynamic_params)
                differences['unique_word'] = unique_word

    return differences

# Function to save the flagged URLs to a text file
def save_flagged_urls(url, filename):
    with open(filename, 'a') as file:
        file.write(url + '\n')

# Function to run recollapse tool and save results to a text file
def run_recollapse(url, original_responses, dynamic_params):
    redirect_uri_match = re.search(r'redirect_uri=(https?://[^&]*)', url)
    if not redirect_uri_match:
        print(f"Failed to extract domain from redirect_uri: {url}")
        return

    domain = redirect_uri_match.group(1)
    print(f"Running recollapse on redirect_uri domain: {domain}")

    recollapse_output = f"{hashlib.md5(domain.encode('utf-8')).hexdigest()}-recollapse.txt"
    subprocess.run(f'recollapse -an {domain} >> {recollapse_output}', shell=True, text=True)

    # Create the fuzzed URL by replacing the redirect_uri value with FUZZ
    fuzzed_url = url.replace(domain, 'FUZZ')

    ffuf_output = f"{hashlib.md5(url.encode('utf-8')).hexdigest()}-ffuf.txt"

    differences = check_response_change(url, original_responses, dynamic_params)
    if differences:
        if 'html_diff' in differences:
            unique_word = differences.get('unique_word')
            if unique_word:
                ffuf_command = f'ffuf -w {recollapse_output} -u "{fuzzed_url}" -mr "{unique_word}" -t 10 -p "1.0" | tee {ffuf_output}'
                subprocess.run(ffuf_command, shell=True, text=True)
    else:
        print("No differences found in the initial requests. Using -mr for ffuf.")
        ffuf_command = f'ffuf -w {recollapse_output} -u "{fuzzed_url}" -mr "unique-word" -t 10 -p "1.0" | tee {ffuf_output}'
        subprocess.run(ffuf_command, shell=True, text=True)

# Main function to process URLs from the input file
def main(input_file):
    with open(input_file, 'r') as file:
        urls = file.readlines()

    for url in urls:
        url = url.strip()
        print(f"Processing URL: {url}")

        # Step 1: Make multiple GET requests and store the responses
        original_responses = make_get_request_curl(url, num_requests=10)

        if original_responses is None or len(original_responses) < 10:
            print(f"Failed to make multiple GET requests for URL: {url}")
            continue

        # Step 2: Identify potential dynamic parameters
        dynamic_params = identify_dynamic_parameters(original_responses)

        # Step 3: Check for changes in responses and get observed differences
        differences = check_response_change(url, original_responses, dynamic_params)

        if differences:
            # Step 4: Save the flagged URL to a text file
            save_flagged_urls(url, "flagged_urls.txt")

            # Step 5: Run recollapse tool on redirect_uri domain and save results to a text file
            run_recollapse(url, original_responses, dynamic_params)

if __name__ == "__main__":
    input_file = "urls.txt"  # Replace with the path to your input file containing URLs
    main(input_file)
