import httpagentparser


class RequestUserAgentParser:

    @classmethod
    def get_short_agent_string(cls, request):
        data = httpagentparser.simple_detect(str(request.user_agent))
        return f'{data[1].split(".")[0]}/{data[0].split(" ")[0]}'