"""Gemini agent implementation for scientific writer."""

import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable
from pathlib import Path

import google.generativeai as genai
from google.generativeai.types import content_types

# Configure logging
logger = logging.getLogger("scientific_writer.gemini")

class GeminiAgent:
    """A Gemini-based agent that mimics the claude-agent-sdk tool-calling interface."""

    def __init__(
        self,
        model_name: str,
        api_key: str,
        system_prompt: str,
        allowed_tools: List[str],
        cwd: str,
        max_turns: int = 500
    ):
        self.model_name = model_name
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.allowed_tools = allowed_tools
        self.cwd = Path(cwd).resolve()
        self.max_turns = max_turns

        # Configure the Gemini API
        genai.configure(api_key=self.api_key)

        # Initialize the model
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=self.system_prompt,
            tools=self._get_tool_definitions()
        )

    def _get_tool_definitions(self) -> List[Callable]:
        """Define the tools available to the Gemini agent."""
        # Note: In a real implementation, these would map to the actual tool functions
        # For now, we define them so Gemini knows about them.
        # The execution logic will be in the query loop.

        def Read(path: str) -> str:
            """Read the content of a file.

            Args:
                path: The path to the file to read.
            """
            pass

        def Write(path: str, content: str) -> str:
            """Write content to a file.

            Args:
                path: The path to the file to write.
                content: The content to write to the file.
            """
            pass

        def Edit(path: str, diff: str) -> str:
            """Edit a file using a git-style diff.

            Args:
                path: The path to the file to edit.
                diff: The git-style diff to apply.
            """
            pass

        def Bash(command: str) -> str:
            """Execute a bash command.

            Args:
                command: The bash command to execute.
            """
            pass

        def WebSearch(query: str) -> str:
            """Search the web for information.

            Args:
                query: The search query.
            """
            pass

        def research_lookup(query: str) -> str:
            """Perform a deep research lookup for academic papers.

            Args:
                query: The research query.
            """
            pass

        # Map allowed_tools to these functions
        tool_map = {
            "Read": Read,
            "Write": Write,
            "Edit": Edit,
            "Bash": Bash,
            "WebSearch": WebSearch,
            "research-lookup": research_lookup
        }

        return [tool_map[t] for t in self.allowed_tools if t in tool_map]

    async def _execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Execute a tool and return the result as a string."""
        # This is where the actual tool execution logic goes.
        # Since we want to use the same tools as the Claude version,
        # we'll need to implement them or call existing implementations.

        # For the purpose of this implementation, we'll implement the basic ones
        # that are typically used by Scientific Writer.

        if name == "Read":
            path = self.cwd / args.get("path", "")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                return f"Error reading file: {str(e)}"

        elif name == "Write":
            path = self.cwd / args.get("path", "")
            content = args.get("content", "")
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return f"Successfully wrote to {path}"
            except Exception as e:
                return f"Error writing file: {str(e)}"

        elif name == "Bash":
            command = args.get("command", "")
            try:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.cwd)
                )
                stdout, stderr = await process.communicate()
                result = stdout.decode()
                if stderr:
                    result += "\nErrors:\n" + stderr.decode()
                return result or "Command executed (no output)"
            except Exception as e:
                return f"Error executing command: {str(e)}"

        elif name == "Edit":
            path = self.cwd / args.get("path", "")
            diff = args.get("diff", "")
            try:
                # Basic diff application logic (mimics git apply)
                # In a real system, this would use a robust library
                # For now, we'll use a bash command as it's more reliable
                diff_path = self.cwd / f".temp_diff_{os.getpid()}.patch"
                with open(diff_path, "w", encoding="utf-8") as f:
                    f.write(diff)

                cmd = f"patch {path} {diff_path}"
                result = await self._execute_tool("Bash", {"command": cmd})

                # Clean up
                if diff_path.exists():
                    diff_path.unlink()

                return f"Applied edit to {path}:\n{result}"
            except Exception as e:
                return f"Error editing file: {str(e)}"

        elif name == "WebSearch":
            query = args.get("query", "")
            # We'll use the existing search skill if available
            script_path = self.cwd / ".claude" / "skills" / "parallel-web" / "scripts" / "parallel_web.py"
            if script_path.exists():
                cmd = f"python {script_path} search \"{query}\""
                return await self._execute_tool("Bash", {"command": cmd})
            else:
                # Fallback to simple bash-based search if script not found
                # (This is just a placeholder, actual implementation should be robust)
                return f"WebSearch tool (parallel_web.py) not found in {script_path}"

        elif name == "research-lookup":
            query = args.get("query", "")
            # Check in the common locations for research-lookup
            locations = [
                self.cwd / "research_lookup.py",
                self.cwd / ".claude" / "skills" / "research-lookup" / "research_lookup.py",
                Path(__file__).parent.parent / "research_lookup.py"
            ]

            script_path = None
            for loc in locations:
                if loc.exists():
                    script_path = loc
                    break

            if script_path:
                cmd = f"python {script_path} \"{query}\""
                return await self._execute_tool("Bash", {"command": cmd})
            else:
                return "research-lookup tool not found"

        # Add more tools as needed
        return f"Tool {name} not implemented in Gemini backend"

    async def query(self, prompt: str) -> AsyncGenerator[Any, None]:
        """Execute a query and yield messages (similar to claude-agent-sdk)."""
        chat = self.model.start_chat()

        # Initial message
        current_input = prompt

        turn_count = 0
        while turn_count < self.max_turns:
            turn_count += 1

            try:
                response = await chat.send_message_async(current_input)
            except Exception as e:
                logger.error(f"Error in Gemini chat: {str(e)}")
                break

            if not response.candidates:
                logger.error("Gemini returned no candidates")
                break

            # Yield the assistant message
            class MockMessage:
                def __init__(self, response):
                    self.content = []
                    # Basic token usage if available (Gemini usage metadata)
                    self.usage = None
                    if hasattr(response, "usage_metadata"):
                        class Usage:
                            def __init__(self, metadata):
                                self.input_tokens = metadata.prompt_token_count
                                self.output_tokens = metadata.candidates_token_count
                                self.cache_creation_input_tokens = 0
                                self.cache_read_input_tokens = 0
                        self.usage = Usage(response.usage_metadata)

                    for part in response.candidates[0].content.parts:
                        if part.text:
                            class TextBlock:
                                def __init__(self, text):
                                    self.text = text
                            self.content.append(TextBlock(part.text))

                        if part.function_call:
                            class ToolUseBlock:
                                def __init__(self, fc):
                                    self.type = "tool_use"
                                    self.name = fc.name
                                    self.input = dict(fc.args)
                            self.content.append(ToolUseBlock(part.function_call))

            yield MockMessage(response)

            # Check if there are tool calls
            tool_calls = [p.function_call for p in response.candidates[0].content.parts if p.function_call]
            if not tool_calls:
                break

            # Execute tool calls and send results back
            tool_responses = []
            for tc in tool_calls:
                result = await self._execute_tool(tc.name, dict(tc.args))

                # Gemini expects FunctionResponse objects
                tool_responses.append({
                    "function_response": {
                        "name": tc.name,
                        "response": {"result": result}
                    }
                })

            # Send back the tool responses
            current_input = tool_responses

async def gemini_query(prompt: str, options: Any) -> AsyncGenerator[Any, None]:
    """Compatible wrapper for generate_paper's claude_query call."""

    # Try different attribute names as ClaudeAgentOptions may differ
    cwd = getattr(options, "cwd", os.getcwd())
    max_turns = getattr(options, "max_turns", 500)

    agent = GeminiAgent(
        model_name=options.model,
        api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
        system_prompt=options.system_prompt,
        allowed_tools=options.allowed_tools,
        cwd=cwd,
        max_turns=max_turns
    )

    async for message in agent.query(prompt):
        yield message
