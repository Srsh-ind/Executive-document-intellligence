## Setup and Run Instructions
## Follow the steps below to install dependencies, start the vLLM server, and run the Streamlit app.

## 1. Install project dependencies
    Run the following commands in the terminal from the project root folder:
    pip install -r requirements.txt
    pip install "chromadb>=0.5.0"
## 2. Install Streamlit, If Streamlit is not already installed, run:
    pip install streamlit --ignore-installed blinker
## 3. Install compatibility packages, Run the following command to avoid dependency/version conflicts:
    pip install "starlette<0.49.0" "protobuf<7.0.0" "numpy<2.3"
## 4. Start the vLLM server, Open a terminal and run:
    vllm serve Qwen/Qwen2-7B-Instruct --port 8000 --gpu-memory-utilization 0.3
## 5. Start the Streamlit app, Open another terminal and run:
    python -m streamlit run app.py \
      --server.port 8501 \
      --server.headless true \
      --server.enableCORS false \
      --server.enableXsrfProtection false
