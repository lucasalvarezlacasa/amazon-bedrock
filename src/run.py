import json
import logging
import os

import boto3
from botocore.client import BaseClient
from botocore.eventstream import EventStream
from dotenv import load_dotenv

from src.dto import (
    ConverseModelDto,
    ConverseInferenceConfig,
    ConverseContentDto,
    ConverseMessageDto,
    AdditionalModelRequestFieldsDto,
)
from src.utils import (
    BedrockWrapper,
    BedrockRuntimeWrapper,
    InvokeModelDto,
    BedrockSTSWrapper,
)


def usage_demo() -> None:
    load_dotenv()  # Load required ENV vars to use Bedrock
    region: str = os.environ["AWS_REGION"]

    # Fetch token
    print("Generate a token for the session...")
    sts_client: BaseClient = boto3.client(
        "sts",
        region_name=region,
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    )
    new_access_key, new_secret_key, new_session_token = BedrockSTSWrapper(sts_client).get_credentials()
    print("Token successfully generated!")

    # Create wrappers
    bedrock_wrapper: BedrockWrapper = BedrockWrapper(
        boto3.client(
            service_name="bedrock",
            region_name=region,
            aws_access_key_id=new_access_key,
            aws_secret_access_key=new_secret_key,
            aws_session_token=new_session_token,
        )
    )
    runtime_wrapper: BedrockRuntimeWrapper = BedrockRuntimeWrapper(
        boto3.client(
            service_name="bedrock-runtime",
            region_name=region,
            aws_access_key_id=new_access_key,
            aws_secret_access_key=new_secret_key,
            aws_session_token=new_session_token,
        )
    )

    # List foundation models
    print("\n\nListing some available foundation models: ============================")
    models: list[dict] = bedrock_wrapper.list_foundation_models()[:5]
    for model in models:
        print(f"- Model ID: {model['modelId']}")
        print(f"  Name: {model['modelName']}")
        print(f"  Provider: {model['providerName']}")
        print()

    # Get details of a specific model. Model needs to be enabled beforehand!
    model_id: str = "meta.llama3-8b-instruct-v1:0"
    print(f"\nGetting details for model: {model_id} ==================================")
    model_details = bedrock_wrapper.get_foundation_model(model_id)
    print(json.dumps(model_details, indent=4))
    print(f"Does model support streaming? {model_details['responseStreamingSupported']}")

    # Invoke the model
    do_invoke_api(model_id, runtime_wrapper)

    # Converse
    do_converse_api(model_id, runtime_wrapper)


def do_invoke_api(model_id: str, runtime_wrapper: BedrockRuntimeWrapper) -> None:
    print(f"\n\nInvoking model: {model_id} (NO STREAMING) ==================================")
    prompt: str = """
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>
    You are a helpful AI assistant for travel tips and recommendations<|eot_id|><|start_header_id|>user<|end_header_id|>
    What can you help me with?<|eot_id|><|start_header_id|>assistant<|end_header_id|>
    """
    response_text: str = runtime_wrapper.invoke_model(
        model_id=model_id, invocation_dto=InvokeModelDto(prompt=prompt, max_gen_len=512, temperature=0.7, top_p=0.9)
    )
    print(f"Model response:\n{response_text}")

    print(f"\n\nInvoking model: {model_id} (WITH STREAMING) ==================================")
    response_stream: EventStream = runtime_wrapper.invoke_model_with_stream(
        model_id=model_id, invocation_dto=InvokeModelDto(prompt=prompt, max_gen_len=512, temperature=0.7, top_p=0.9)
    )
    for event in response_stream:
        chunk = event["chunk"]  # Extract the chunk of data from the event
        print(chunk)


def do_converse_api(model_id: str, runtime_wrapper: BedrockRuntimeWrapper) -> None:
    print(f"\n\nInvoking converse model: {model_id} (NO STREAMING) ==================================")
    converse_dto: ConverseModelDto = ConverseModelDto(
        system_prompts=[
            ConverseContentDto(
                text="You are an app that creates playlists for a radio station that plays rock and pop music. "
                     "Only return song names and the artist."
            )
        ],
        messages=[ConverseMessageDto(role="user", content=[ConverseContentDto(text="Create a list of 10 pop songs.")])],
        inference_config=ConverseInferenceConfig(max_tokens=512, temperature=0.5),  # type: ignore
        additional_model_request_fields=AdditionalModelRequestFieldsDto(top_k=200),  # type: ignore
    )
    response_text: str = runtime_wrapper.converse_model(model_id=model_id, converse_dto=converse_dto)
    print(f"Model response:\n{response_text}")

    print(f"\n\nInvoking converse model: {model_id} (STREAMING) ==================================")
    response_stream: EventStream = runtime_wrapper.converse_model_with_stream(
        model_id=model_id, converse_dto=converse_dto
    )
    for chunk in response_stream:
        if "contentBlockDelta" in chunk:
            text = chunk["contentBlockDelta"]["delta"]["text"]
            print(text, end="")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    usage_demo()
