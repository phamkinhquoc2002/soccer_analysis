agent_role_template = """
< Role >
{}
</ Role >
"""

agent_tool_template = """
< Tools >
{}
</ Tools >
"""

agent_instruction_template = """
< Instructions >
{}
</ Instructions >"""

tool_calling_prompt_template = """
All Tools called up to this point:
{}
User's request:
{}
Metrics to analyze from the previous agent:
{}
Reason why you choose the previous tool:
{}
Previous tool name: 
{}
Previous tool result:
{}
"""