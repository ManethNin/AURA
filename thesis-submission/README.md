# Automatically Fixing Dependency Breaking Changes

This repository contains the code and data for the study "Automatically Fixing Dependency Breaking Changes". Our research investigates the effectiveness of Large Language Models (LLMs) in automating the process of resolving breaking changes caused by dependency updates in Java projects.

## Repository Structure

The main branch is partitioned into two submodules:

1. `zero-shot`: Contains the implementation of the zero-shot prompting approach.
2. `agent`: Contains the implementation of the agentic approach.

Each submodule links to a specific branch in the repository, representing the respective states of both implementations.

## Study Overview

Our study compares two distinct approaches for automatically fixing breaking changes in dependency updates:

1. Zero-shot prompting: Utilizing LLMs to generate solutions without prior examples or instructions.
2. Agentic approach: Allowing LLMs to autonomously refine solutions based on environmental feedback.

We evaluate these approaches using a curated dataset of breaking changes in Java projects, focusing on their ability to handle API incompatibilities introduced by dependency updates.

## Dataset

The full dataset used in this study is available on Zenodo. To maintain anonymity during the review process, we have omitted the direct link in this README. The dataset contains:

- Curated examples of breaking changes in Java projects
- API change information
- Compilation and test suite errors
- LLM interaction traces (OpenInference format)


## Replication

There are three ways to replicate our study:

### 1. Analysis Replication

To replicate our analysis:

1. Clone this repository and its submodules:
   ```
   git clone --recursive [repository-url]
   ```
> [!IMPORTANT]  
> When reviewing this artifact, please find this repository with the dataset and skip step 2.

2. Download the dataset from Zenodo.
3. Use the Jupyter notebooks provided in each submodule to analyze the data:

   - In the `agent` folder:
     - `agent_langchain.ipynb`
     - `agent_simplified.ipynb`
     - `analysis/parse_errors.ipynb`
     - `analysis/total_tokens.ipynb`
     - `analysis/trace-analysis.ipynb` <- Most analysis logic is in this notebook
     - `patch-analysis.ipynb`
     - `replicator.ipynb`

   - In the `zero-shot` folder:
     - `dspy-trace-analysis.ipynb` <- Most analysis logic is in this notebook
     - `patch-analysis.ipynb`
     - `replicator.ipynb`
     - `reproduce_failing_diff/experiment.ipynb`

### 2. Full Experiment Replication

To run the full experiments:

1. Follow step 1 from the Analysis Replication section.
2. Set up the required API keys:
   - Create a `.env` file in each submodule folder (`agent` and `zero-shot`) with the following keys:
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
   - Fill in the appropriate values for each API key.
3. Follow the setup instructions in each submodule's README for additional environment configuration.
4. Run the experiment notebooks as described in the respective submodule documentation.

Note: Full replication requires access to the various LLM APIs and may incur costs. Ensure you have the necessary permissions and budget before proceeding with full replication.

### 3. Repair Replication with Docker

To replicate specific repairs using our pre-built Docker images:

1. Ensure you have Docker installed on your system.

2. Pull the desired Docker image using the command line. For example:

   ```
   docker pull ghcr.io/[anonymized-repo-slug]:claude-3.5-sonnet-7e8c62e2bb21097e563747184636cf8e8934ce98-reproduction
   ```

> [!IMPORTANT]  
> When reviewing this code via Zenodo and attempting replication, please use the included `docker-images.zip`, which first has to be unzipped, after which the images can be loaded as follows: `docker load < image_name.tar.gz` Please kindly proceed with the instructions below after.

1. Run the Docker container:

   ```
   docker run -it [image-name]
   ```

These Docker images contain the state of projects after repair attempts, allowing for easy inspection and verification of the changes made by our automated repair system.