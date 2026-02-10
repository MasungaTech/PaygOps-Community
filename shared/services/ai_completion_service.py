import os
import re
import anthropic
import config


class AICompletionService:

    @classmethod
    def get_completion(cls, prompt_template, prompt_user_inputs=None):
        # Use Claude Sonnet 4.5 (latest version as of 2025)
        MODEL_VERSION = 'claude-sonnet-4-5'
        MAX_ANSWER_SIZE = 8192
        if prompt_user_inputs:
            formatted_prompt = cls.custom_format(prompt_template, prompt_user_inputs)
        else:
            formatted_prompt = prompt_template


        os.environ["ANTHROPIC_API_KEY"] = config.ANTHROPIC_API_KEY
        claude = anthropic.Anthropic()
        try:
            response = claude.messages.create(
                model=MODEL_VERSION,
                messages=[
                    {"role": "user", "content": formatted_prompt}
                ],
                max_tokens=MAX_ANSWER_SIZE
            )
            return str(response.content[0].text)
        except anthropic.APIError as e:
            # Provide detailed error information
            error_msg = str(e)
            # Try to get status code if available
            status_code = getattr(e, 'status_code', None)  # type: ignore
            if status_code:
                error_msg = f"Error code: {status_code} - {error_msg}"
            # Try to get body if available
            body = getattr(e, 'body', None)  # type: ignore
            if body:
                error_msg += f" Data: {body}"
            raise Exception(f"Anthropic API error with model '{MODEL_VERSION}': {error_msg}") from e

    @classmethod
    def custom_format(cls, template, replacements, open_delim='<<', close_delim='>>'):
        # Escape delimiters for regex
        open_delim_escaped = re.escape(open_delim)
        close_delim_escaped = re.escape(close_delim)
        
        # Regex to match placeholders
        pattern = f"{open_delim_escaped}(.*?){close_delim_escaped}"
        
        # Replace each match with the corresponding value from replacements
        def replace_match(match):
            key = match.group(1).strip()  # Extract the key
            return str(replacements.get(key, match.group(0)))  # Return replacement or original
        
        return re.sub(pattern, replace_match, template)