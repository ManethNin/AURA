# Agentic Implementation

## Overview

This project includes various scripts and notebooks for data analysis, machine learning, and other tasks. The primary entry point for running experiments is the `langchain-agent.py` script. Given that the experiments can take a longer time, it is recommended to use `tmux` to manage the sessions.

## Prerequisites

- Python 3.12.3 (any other version _might_ work)
- `pdm` (Python Development Master)
- `tmux` (optional but recommended for long-running experiments)

## Installation

1. Clone the repository:
    ```sh
    git clone <repository-url>
    cd <project-directory>
    ```

2. Install `pdm` if you haven't already:
    ```sh
    pip install pdm
    ```

3. Install the project dependencies using `pdm`:
    ```sh
    pdm install
    ```
4. Ensure that you have Docker installed and running on your system. For macOS users, we recommend using Colima as it provides an easy-to-use Docker environment. We mount the necessary files into the `/tmp/colima` directory for proper functionality on macos, therefore any other macos setup would have to support this mounting path.

5. Set up the required API keys:
   - Create a `.env` file with the following keys:
     ```
     OPENAI_API_KEY=
     ANTHROPIC_API_KEY=
     TOGETHER_API_KEY=
     MISTRAL_API_KEY=
     GOOGLE_APPLICATION_CREDENTIALS=
     GITHUB_TOKEN=
     AZURE_OPENAI_ENDPOINT=
     AZURE_OPENAI_API_KEY=
     ```

## Usage

### Running the LangChain Agent

1. It is recommended to use `tmux` to manage long-running sessions. Start a new `tmux` session:
    ```sh
    tmux new -s agentic_experiment
    ```

2. Run the `langchain-agent.py` script:
    ```sh
    pdm run python langchain-agent.py
    ```

3. To detach from the `tmux` session, press `Ctrl + B` followed by `D`. You can reattach to the session later using:
    ```sh
    tmux attach -t langchain_experiment
    ```

### Additional Scripts and Notebooks

- To run other Jupyter notebooks, use the following command:
    ```sh
    pdm run jupyter notebook
    ```

- To run other Python scripts, use the following command:
    ```sh
    pdm run python <script-name>.py
    ```
