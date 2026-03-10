"""
Introduction to PydanticAI.

This module demonstrates how PydanticAI makes it easier to build
production-grade LLM-powered systems with type safety and structured responses.
"""

from typing import Dict, List, Optional
import nest_asyncio
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext, Tool
from pydantic_ai.models.google import GoogleModel

from utils.markdown import to_markdown

load_dotenv()
nest_asyncio.apply()


model = GoogleModel("gemini-2.5-flash")

# --------------------------------------------------------------
# 1. Simple Agent - Hello World Example
# --------------------------------------------------------------
"""
This example demonstrates the basic usage of PydanticAI agents.
Key concepts:
- Creating a basic agent with a system prompt
- Running synchronous queries
- Accessing response data, message history, and costs
"""

# agent1 = Agent(
#     model=model,
#     system_prompt="당신은 매우 사려깊은 고객 서포트 에이전트입니다. 당신은 고객의 질문에 대해 매우 정확하게 답변해주세요.",
# )

# # Example usage of basic agent
# response = agent1.run_sync("어떻게 주문을 추적할 수 있나요?")
# print(response.output)
# print(response.all_messages())
# print(response.usage())


# response2 = agent1.run_sync(
#     user_prompt="이전 질문이 뭐야?",
#     message_history=response.new_messages(),
# )
# print(response2.output)

# # --------------------------------------------------------------
# # 2. Agent with Structured Response
# # --------------------------------------------------------------
# """
# 이 예제는 에이전트로부터 구조화되고 타입 안전한 응답을 받는 방법을 보여줍니다.
# 주요 개념:
# - Pydantic 모델을 사용하여 응답 구조 정의
# - 타입 검증 및 안전성
# - 모델의 이해를 돕기 위한 필드 설명
# """


class ResponseModel(BaseModel):
    """Structured response with metadata."""

    response: str
    needs_escalation: bool
    follow_up_required: bool
    sentiment: str = Field(description="Customer sentiment analysis")


# agent2 = Agent(
#     model=model,
#     output_type=ResponseModel,
#     system_prompt=(
#         "당신은 매우 사려깊은 고객 서포트 에이전트입니다. 당신은 고객의 질문에 대해 매우 정확하게 답변해주세요."
#         "Analyze queries carefully and provide structured responses."
#     ),
# )

# response = agent2.run_sync("어떻게 주문을 추적할 수 있나요?")
# print(response.output.model_dump_json(indent=2))


# # --------------------------------------------------------------
# # 3. Agent with Structured Response & Dependencies
# # --------------------------------------------------------------
"""
This example demonstrates how to use dependencies and context in agents.
Key concepts:
- Defining complex data models with Pydantic
- Injecting runtime dependencies
- Using dynamic system prompts
"""


# Define order schema
class Order(BaseModel):
    """Structure for order details."""

    order_id: str
    status: str
    items: List[str]


# Define customer schema
class CustomerDetails(BaseModel):
    """Structure for incoming customer queries."""

    customer_id: str
    name: str
    email: str
    orders: Optional[List[Order]] = None


# # Agent with structured output and dependencies
# agent5 = Agent(
#     model=model,
#     output_type=ResponseModel,
#     deps_type=CustomerDetails,
#     retries=3,
#     system_prompt=(
#         "You are an intelligent customer support agent. "
#         "Analyze queries carefully and provide structured responses. "
#         "Always great the customer and provide a helpful response."
#     ),  # These are known when writing the code
# )


# # Add dynamic system prompt based on dependencies
# @agent5.system_prompt
# async def add_customer_name(ctx: RunContext[CustomerDetails]) -> str:
#     return f"Customer details: {to_markdown(ctx.deps)}"  # These depend in some way on context that isn't known until runtime


# customer = CustomerDetails(
#     customer_id="1",
#     name="John Doe",
#     email="john.doe@example.com",
#     orders=[
#         Order(order_id="12345", status="shipped", items=["Blue Jeans", "T-Shirt"]),
#     ],
# )

# response = agent5.run_sync(user_prompt="What did I order?", deps=customer)

# response.all_messages()
# print(response.output.model_dump_json(indent=2))

# print(
#     "Customer Details:\n"
#     f"Name: {customer.name}\n"
#     f"Email: {customer.email}\n\n"
#     "Response Details:\n"
#     f"{response.output.response}\n\n"
#     "Status:\n"
#     f"Follow-up Required: {response.output.follow_up_required}\n"
#     f"Needs Escalation: {response.output.needs_escalation}"
# )


# # --------------------------------------------------------------
# # 4. Agent with Tools
# # --------------------------------------------------------------

"""
This example shows how to enhance agents with custom tools.
Key concepts:
- Creating and registering tools
- Accessing context in tools
"""

shipping_info_db: Dict[str, str] = {
    "12345": "Shipped on 2024-12-01",
    "67890": "Out for delivery",
}


def get_shipping_info(ctx: RunContext[CustomerDetails]) -> str:
    """Get the customer's shipping information."""
    return shipping_info_db[ctx.deps.orders[0].order_id]


# Agent with structured output and dependencies
agent5 = Agent(
    model=model,
    output_type=ResponseModel,
    deps_type=CustomerDetails,
    retries=3,
    system_prompt=(
        "You are an intelligent customer support agent. "
        "Analyze queries carefully and provide structured responses. "
        "Use tools to look up relevant information."
        "Always great the customer and provide a helpful response."
    ),  # These are known when writing the code
    tools=[Tool(get_shipping_info, takes_ctx=True)],  # Add tool via kwarg
)


@agent5.system_prompt
async def add_customer_name(ctx: RunContext[CustomerDetails]) -> str:
    return f"Customer details: {to_markdown(ctx.deps)}"


response = agent5.run_sync(
    user_prompt="What's the status of my last order?", deps=customer
)

response.all_messages()
print(response.output.model_dump_json(indent=2))

print(
    "Customer Details:\n"
    f"Name: {customer.name}\n"
    f"Email: {customer.email}\n\n"
    "Response Details:\n"
    f"{response.output.response}\n\n"
    "Status:\n"
    f"Follow-up Required: {response.output.follow_up_required}\n"
    f"Needs Escalation: {response.output.needs_escalation}"
)

 
# # --------------------------------------------------------------
# # 5. Agent with Reflection and Self-Correction
# # --------------------------------------------------------------

# """
# This example demonstrates advanced agent capabilities with self-correction.
# Key concepts:
# - Implementing self-reflection
# - Handling errors gracefully with retries
# - Using ModelRetry for automatic retries
# - Decorator-based tool registration
# """

# # Simulated database of shipping information
# shipping_info_db: Dict[str, str] = {
#     "#12345": "Shipped on 2024-12-01",
#     "#67890": "Out for delivery",
# }

# customer = CustomerDetails(
#     customer_id="1",
#     name="John Doe",
#     email="john.doe@example.com",
# )

# # Agent with reflection and self-correction
# agent5 = Agent(
#     model=model,
#     output_type=ResponseModel,
#     deps_type=CustomerDetails,
#     retries=3,
#     system_prompt=(
#         "You are an intelligent customer support agent. "
#         "Analyze queries carefully and provide structured responses. "
#         "Use tools to look up relevant information. "
#         "Always greet the customer and provide a helpful response."
#     ),
# )


# @agent5.tool_plain()  # Add plain tool via decorator
# def get_shipping_status(order_id: str) -> str:
#     """Get the shipping status for a given order ID."""
#     shipping_status = shipping_info_db.get(order_id)
#     if shipping_status is None:
#         raise ModelRetry(
#             f"No shipping information found for order ID {order_id}. "
#             "Make sure the order ID starts with a #: e.g, #624743 "
#             "Self-correct this if needed and try again."
#         )
#     return shipping_info_db[order_id]


# # Example usage
# response = agent5.run_sync(
#     user_prompt="What's the status of my last order 12345?", deps=customer
# )

# response.all_messages()
# print(response.output.model_dump_json(indent=2))
