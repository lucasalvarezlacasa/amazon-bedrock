from typing import Literal, Any

from pydantic import BaseModel, Field


class InvokeModelDto(BaseModel):
    # https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-meta.html
    prompt: str
    temperature: float = 0.7
    top_p: float = 0.9
    max_gen_len: int = 512


class PopulationByFieldTypeDto(BaseModel):
    class Config:
        allow_population_by_field_name = True  # Allow setting fields by their Python names


class ConverseInferenceConfig(PopulationByFieldTypeDto):
    max_tokens: int = Field(512, alias="maxTokens")
    temperature: float | None = 0.7
    top_p: float | None = Field(0.9, alias="topP")
    stop_sequences: list[str] = Field(default_factory=list, alias="stopSequences")


class ConverseContentDto(PopulationByFieldTypeDto):
    # There are more possibilities, I just included this one
    text: str


class ConverseMessageDto(BaseModel):
    role: Literal["user", "assistant"]
    content: list[ConverseContentDto]


class AdditionalModelRequestFieldsDto(BaseModel):
    top_k: int | None = Field(None, alias="topK")


class ConverseModelDto(BaseModel):
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime/client/converse.html
    system_prompts: list[ConverseContentDto]
    messages: list[ConverseMessageDto]
    inference_config: ConverseInferenceConfig
    additional_model_request_fields: AdditionalModelRequestFieldsDto

    def to_client_payload(self) -> dict[str, Any]:
        # Convert the model into the exact payload format for the Bedrock client
        return {
            "system": [prompt.model_dump() for prompt in self.system_prompts],
            "messages": [message.model_dump() for message in self.messages],
            "inferenceConfig": self.inference_config.model_dump(by_alias=True),
            "additionalModelRequestFields": self.additional_model_request_fields.model_dump(exclude_none=True),
        }
