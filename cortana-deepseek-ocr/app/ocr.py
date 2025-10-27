from vllm import LLM, SamplingParams
from vllm.model_executor.models.deepseek_ocr import NGramPerReqLogitsProcessor
from PIL import Image

# Initialize model once at startup
llm = LLM(
    model="deepseek-ai/DeepSeek-OCR",
    enable_prefix_caching=False,
    mm_processor_cache_gb=0,
    logits_processors=[NGramPerReqLogitsProcessor]
)

def extract_text(image_path: str, prompt: str = "<image>\nFree OCR.") -> str:
    image = Image.open(image_path).convert("RGB")
    sampling_param = SamplingParams(
        temperature=0.0,
        max_tokens=8192,
        extra_args=dict(
            ngram_size=30,
            window_size=90,
            whitelist_token_ids={128821, 128822},
        ),
        skip_special_tokens=False,
    )

    model_input = [{"prompt": prompt, "multi_modal_data": {"image": image}}]
    result = llm.generate(model_input, sampling_param)
    return result[0].outputs[0].text
