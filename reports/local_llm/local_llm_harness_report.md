# Local LLM Harness Report

Timestamp: 2025-12-13T19:43:49.749Z
Runner: tools\bin\llama.cpp\llama-run.exe
Model path: tools\models\Qwen2.5-Omni-7B-Q4_K_M.gguf
Status: OK

Details:
```
{
  "status": "OK",
  "started_at_utc": "2025-12-13T19:43:49.841Z",
  "ended_at_utc": "2025-12-13T19:43:49.850Z",
  "duration_ms": 9,
  "return_code": 1,
  "stdout": "Description:\n  Runs a llm\n\nUsage:\n  llama-run [options] model [prompt]\n\nOptions:\n  -c, --context-size <value>\n      Context size (default: 2048)\n  --chat-template-file <path>\n      Path to the file containing the chat template to use with the model.\n      Only supports jinja templates and implicitly sets the --jinja flag.\n  --jinja\n      Use jinja templating for the chat template of the model\n  -n, -ngl, --ngl <value>\n      Number of GPU layers (default: 999)\n  --temp <value>\n      Temperature (default: 0.8)\n  -t, --threads <value>\n      Number of threads to use during generation (default: 4)\n  -v, --verbose, --log-verbose\n      Set verbosity level to infinity (i.e. log all messages, useful for debugging)\n  -h, --help\n      Show help message\n\nCommands:\n  model\n      Model is a string with an optional prefix of \n      huggingface:// (hf://), modelscope:// (ms://), ollama://, https:// or file://.\n      If no protocol is specified and a file exists in the specified\n      path, file:// is assumed, otherwise if a file does not exist in\n      the specified path, ollama:// is assumed. Models that are being\n      pulled are downloaded with .partial extension while being\n      downloaded and then renamed as the file without the .partial\n      extension when complete.\n\nExamples:\n  llama-run llama3\n  llama-run ollama://granite-code\n  llama-run ollama://smollm:135m\n  llama-run hf://QuantFactory/SmolLM-135M-GGUF/SmolLM-135M.Q2_K.gguf\n  llama-run huggingface://bartowski/SmolLM-1.7B-Instruct-v0.2-GGUF/SmolLM-1.7B-Instruct-v0.2-IQ3_M.gguf\n  llama-run ms://QuantFactory/SmolLM-135M-GGUF/SmolLM-135M.Q2_K.gguf\n  llama-run modelscope://bartowski/SmolLM-1.7B-Instruct-v0.2-GGUF/SmolLM-1.7B-Instruct-v0.2-IQ3_M.gguf\n  llama-run https://example.com/some-file1.gguf\n  llama-run some-file2.gguf\n  llama-run file://some-file3.gguf\n  llama-run --ngl 999 some-file4.gguf\n  llama-run --ngl 999 some-file5.gguf Hello World\n",
  "stderr": "Error: Failed to parse arguments.\n",
  "model_id": "Qwen2.5-Omni-7B-Q4_K_M",
  "runner": "tools\\bin\\llama.cpp\\llama-run.exe"
}
```
