import time
from smolagents import CodeAgent
from smolagents import LiteLLMModel
from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter

from dotenv import load_dotenv
import os
load_dotenv()

model = LiteLLMModel(
    model_id="gemini/gemini-2.0-flash",
    api_key="YOUR_API_KEY"
)

REMOTE_SSE_SERVER = "http://127.0.0.1:32823/sse"



if __name__ == "__main__":

    # Create List of Requested Tools
    remote_tool_names = ["gemini_web_search"]

    with MCPAdapt({"url": REMOTE_SSE_SERVER},SmolAgentsAdapter()) as tools:
        selected_tools = [tool for tool in tools if tool.name in remote_tool_names]
        selected_tools.extend([]) # add your local tools here
        agent = CodeAgent(tools=selected_tools, model=model, add_base_tools=True)
        agent.run("Please find a remedy for hangover.")


