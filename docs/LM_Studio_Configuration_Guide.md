# LM Studio Configuration Guide for LiteLLM

## Problem Solved
The `LiteLLM.BadRequestError: LLM Provider NOT provided` error occurs when LiteLLM doesn't recognize the model format. This has been fixed by:

1. **Updated Model Format**: Using `lm-studio/llama-3.2-1b-instruct` as requested
2. **Custom Provider Mapping**: Configured LiteLLM to recognize `lm-studio` as a custom provider
3. **Enhanced Error Handling**: Added multiple fallback mechanisms for different model formats

## Configuration Files Updated

### 1. `.env` File
```bash
# LM Studio Configuration
MODEL=lm-studio/llama-3.2-1b-instruct
LMSTUDIO_API_BASE=http://127.0.0.1:1234/v1
LMSTUDIO_API_KEY=lm-studio
```

### 2. `crew.py` File
- Added custom provider mapping for `lm-studio`
- Enhanced error handling with multiple fallback options
- Better logging for debugging

## How to Use

1. **Make sure LM Studio is running** on port 1234 (default)
2. **Load your model** in LM Studio
3. **Run your crew**: `crewai run`

## Troubleshooting

### If you still get provider errors:

1. **Try without provider prefix** - Edit `.env`:
   ```bash
   MODEL=llama-3.2-1b-instruct
   ```

2. **Check LM Studio port** - Ensure LM Studio is running on the correct port:
   ```bash
   LMSTUDIO_API_BASE=http://127.0.0.1:[YOUR_PORT]/v1
   ```

3. **Verify model name** - Use the exact model name from LM Studio:
   ```bash
   MODEL=openai/[EXACT_MODEL_NAME_FROM_LM_STUDIO]
   ```

### Alternative Model Formats to Try

If `openai/llama-3.2-1b-instruct` doesn't work, try these in your `.env`:

```bash
# Option 1: No prefix
MODEL=llama-3.2-1b-instruct

# Option 2: Custom prefix
MODEL=custom/llama-3.2-1b-instruct

# Option 3: Local prefix
MODEL=local/llama-3.2-1b-instruct

# Option 4: Use the exact name from LM Studio
MODEL=openai/bartowski/Llama-3.2-1B-Instruct-GGUF
```

## Verification Steps

1. **Check LM Studio is running**: Visit http://127.0.0.1:1234/v1/models in your browser
2. **Test the API**: 
   ```bash
   curl -X GET "http://127.0.0.1:1234/v1/models" -H "Authorization: Bearer lm-studio"
   ```
3. **Run with debug**: Add `LITELLM_LOG=DEBUG` to your `.env` file

## Common Issues

1. **Port mismatch**: LM Studio default is 1234, but check your actual port
2. **Model not loaded**: Ensure the model is loaded and active in LM Studio
3. **API key**: LM Studio typically doesn't require authentication, but use 'lm-studio' as placeholder

The configuration should now work with your LM Studio setup!