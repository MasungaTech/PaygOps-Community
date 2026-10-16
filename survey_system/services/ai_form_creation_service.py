import json
from shared.api_helpers.server_helpers.jwt_and_schema_verification import validate_schema
from survey_system.form_editor.services import FormService
from survey_system.models.forms import FormVersion
from survey_system.models.forms import Form
from shared.services.ai_completion_service import AICompletionService
from shared.logger.loggers import Error

class AIFormCreationService:

    OPENAPI_SPEC = """
    ```json
"requestBody": {               
    "description": "Form Versions Model with at least the required properties.<br>",
    "content": {
        "application/json": {
            "schema": {"type":"object","properties":{"name":{"description":"This is the name of the form.","type":"string","example":"My Form"},"icon":{"description":"This is the name of the icon of the form. It should use Google Material Symbols.","type":"string","example":"done"},"questions":{"description":"Questions in the form version.","type":"array","items":{"type":"object","properties":{"id":{"type":"integer","example":1234,"description":"This is the ID of the Question. When editing a form, you can specify the ID of the question to use it, if not specified it is assumed that it is a new question. WARNING: You cannot pass both the ID and questions parameters at once."},"slug":{"description":"This is the slug of the Question","type":"string","example":"kids-name"},"name":{"description":"This is the name of the Question","type":"string","example":"Kids Name"},"text":{"description":"This is the text of the Question","type":"string","example":"What is your kid's name?"},"icon":{"description":"This is the icon of the Question. It should use Google's Material Symbols name.","type":"string","example":"home"},"type":{"description":"This is the type of the Question","type":"string","enum":["group","yes_no","text","numeric","choice_text","choice_numeric","picture","long_text","checkbox","date","note","gps","url","signature","gps_surface","integer","regex"],"example":"choice_text"},"min_value":{"description":"This is the minimum value of the Question. For a text question it's the minimum number of characters.","schema":{"oneOf":[{"type":"string","pattern":"^[-+]?[0-9]+$"},{"type":"string","maxLength":0}]},"example":0},"max_value":{"description":"This is the maximum value of the Question. For a text question it's the maximum number of characters.","schema":{"oneOf":[{"type":"string","pattern":"^[-+]?[0-9]+$"},{"type":"string","maxLength":0}]},"example":100},"unit":{"description":"This is the unit of the Question (for numeric questions only)","type":"string","example":"kWh"},"choices":{"description":"These are the choices of the Question (for `choice_text` and `choice_numeric` questions only)","type":"array","items":{"oneOf":[{"type":"string"},{"type":"number"}]},"example":["Alex","Ben","Jeff"]},"min_answers":{"description":"This is the minimum number of answers required for the Question. If set to >1 the question will be required.","schema":{"oneOf":[{"type":"string","pattern":"^[-+]?[0-9]+$"},{"type":"string","maxLength":0}]},"example":1},"max_answers":{"description":"This is the maximum number of answers allowed for the Question.","schema":{"oneOf":[{"type":"string","pattern":"^[-+]?[0-9]+$"},{"type":"string","maxLength":0}]},"example":1},"group":{"description":"This is the group of the Question. When creating a form, put any group ID here to create a group and put the same number on the group questions and the questions part of the group. The group will automatically be created and assigned an ID after creation.","type":"number","example":1},"protected":{"description":"This is the protection status of the Question. If true, the question will only be answerable by someone with the permission to answer protected questions.","type":"boolean","example":true},"additional_data":{"description":"Additional data for regex or picture questions.","type":"object","oneOf":[{"properties":{"regex":{"type":"string","description":"Regular expression for validation (only for regex type questions)","example":"^[a-zA-Z0-9]+$"}},"description":"JSON with regex field for regex question type"},{"properties":{"picture_type":{"type":"integer","description":"The type of picture required for the question (only for picture type questions)","enum":["generic","face_picture","id_credit_card_picture","passport_picture","a4_landscape_picture","a4_portrait_picture"],"example":"1"},"picture_instructions":{"type":"string","description":"Instructions for the picture (optional for picture type questions)","example":"Upload a clear face picture."}},"description":"JSON with picture_type and picture_instructions for picture question type"}}}}},"example":[{"id":1234,"slug":"kids-name","name":"Kids Name","text":"What is your kid's name?","icon":"home","type":"choice_text","min_value":0,"max_value":100,"unit":"kWh","choices":["Alex","Ben","Jeff"],"min_answers":1,"max_answers":1,"group":1,"protected":true,"additional_data":{"regex":"^[a-zA-Z0-9]+$"}}]},"form_id":{"description":"The ID of the base form to which this form version belongs.","type":"integer","example":123},"available_for_leads":{"type":"boolean","example":true,"description":"This the availability of this form for leads."},"available_for_clients":{"type":"boolean","example":true,"description":"This the availability of this form for clients."},"available_for_interactions":{"type":"boolean","example":true,"description":"This the availability of this form for interactions."}},"additionalProperties":false,"required":[]}
        }
    }
}
```

Make sure to include all questions when listed. 
Below is an explanation on the question types for clarity: 
* "yes_no": A boolean input with a selector to choose Yes or no
* "checkbox": A boolean input with a single checkbox. In no cases can it have multiple checkboxes, for multiple choices use "choice_text" with multiple answers. 
* "text": A free text box
* "long_text": A free text box with multiline input
* "numeric": A text box where you can only input numbers
* "integer": A text box where you can only input integers
* "choice_text": A select box with different text options
* "choice_numeric": A select box with different numeric options
* "picture": A field for the user to take a picture. The additional_data for this question type should include picture_type (specifying the type of picture, e.g., "face_picture", "id_credit_card_picture") and picture_instructions (providing instructions on how to take the picture).
    - picture_type (a string) of either 'generic', 'face_picture', 'id_credit_card_picture', 'passport_picture', 'a4_landscape_picture'
    - picture_instructions: providing instructions on how to take the picture.
* "date": A date picker
* "note": Just instructions to the user filling the forms, it is useful to explain the purpose of the form or give details, not as a title. the user cannot enter anything in this question type
* "gps": A gps coordinate picker to pick a single coordinate
* "gps_surface": An input to pick multiple coordinates to draw a polygon on a map (useful for example to measure the size of a crop)
* "url": A text box where you can only input URLs
* "signature": A box to capture a signature
* "regex": A free text box that matches the created regex The additional_data for this question type should include regex (specifying the regex to be used in the question")
Please bear in mind that the context of the user is operations in developing countries mainly for clients at the base of the pyramid. 
    """

    BASE_PROMPT = """Given the following OpenAPI specification for the API to add a form version. Please create the API JSON payload based on the user's prompt. Only output the actual JSON. 

Here is the OpenAPI specification:"""+OPENAPI_SPEC+"""

Here is the user's prompt: 
```
<<user_input>>
```
    """

    FIX_PROMPT = """Given the following OpenAPI specification for the API to add a form version, the previous JSON generated was invalid based on schema validation.
    
    Here is the OpenAPI specification:"""+OPENAPI_SPEC+"""

    Here is the user's prompt: 
            ```
            <<user_input>>
            ```
            The previous JSON output was:
            ```json
            <<ai_generated_output>>
            ```

            The validation error is:
            ```
            <<validation_error>>
            ```
        Please fix the JSON to ensure it adheres to the OpenAPI specification and resolves the validation error. Only output the corrected JSON payload.
    """

    @classmethod
    def create_form(cls, prompt, name, user):
        max_retries = 2
        attempt = 0
        cleaned_output = None

        while attempt < max_retries:
            try:
                # Generate the initial output or retry with fixed JSON
                if cleaned_output is None:
                    ai_generated_output = AICompletionService.get_completion(
                        cls.BASE_PROMPT, prompt_user_inputs={"user_input": prompt}
                    )
                    cleaned_output = cls.clean_ai_generated_output(ai_generated_output)
                else:
                    print(f"Retrying with corrected JSON... Attempt {attempt + 1}")
                
                # Parse the JSON and validate it
                form_data = json.loads(cleaned_output)
                validation_schema = FormVersion.get_model_schema(op='create', for_validate=True)
                validate_schema(form_data, validation_schema)
                
                # Update required fields
                form_data['name'] = name
                form_data['available_for_leads'] = True
                form_data['available_for_clients'] = True

                # Process the form
                form = Form(name=name, icon=form_data.get('icon'))
                form_version = FormService.create(form, questions=form_data.get('questions'))
                return form_version

            except Exception as e:
                # Log the error and try fixing the JSON
                print(f"Validation failed on attempt {attempt + 1}: {str(e)}")
                cleaned_output = cls.fix_json_with_ai(cleaned_output, str(e), prompt)
                attempt += 1
        
        # If all attempts fail, raise a ValueError
        raise Error(f"The prompt:  {prompt} given does not make sense and cannot produce valid JSON. fails with Error: {str(cleaned_output)}")

    
    @classmethod
    def clean_ai_generated_output(cls, ai_generated_output):
        if '```json' in ai_generated_output:
            ai_generated_output = ai_generated_output.split('```json')[1]
        if '```' in ai_generated_output:
            ai_generated_output = ai_generated_output.split('```')[0]
        return ai_generated_output
    
    
    @classmethod
    def fix_json_with_ai(cls, ai_generated_output, validation_error, prompt):
        """
        Prompt the AI to fix the JSON based on the validation error, using `custom_format` for safe formatting.
        """
        # Use custom_format to safely insert JSON and error message into the prompt
        fix_prompt = AICompletionService.custom_format(
            cls.FIX_PROMPT, 
            {"user_input": prompt, "ai_generated_output": ai_generated_output, "validation_error": validation_error}
        )
        
        # Call AI to generate a fixed JSON
        fixed_output = AICompletionService.get_completion(fix_prompt)
        return cls.clean_ai_generated_output(fixed_output)
