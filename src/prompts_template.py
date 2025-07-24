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
User's request:
{}
File name of pre-processed dataset from Specialist Agent:
{}
Reason why you choose the previous tool:
{}
Previous tool name: 
{}
Previous tool result:
{}
"""