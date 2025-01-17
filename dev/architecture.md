# System Architecture Documentation

## Overview

The Problem Solver is an AI-powered system designed to solve Advent of Code problems. This document outlines its architecture and core components.

## Core Systems

### Problem Solving Pipeline

1. **Problem Fetching & Parsing** (`shared/utils.py`, `shared/parser.py`)
   - Fetches problem text and input from Advent of Code
   - Parses problem descriptions into structured format
   - Extracts test cases and requirements

2. **Solution Generation** (`shared/llm/`)
   - Model Management (`models.py`, `providers.py`)
   - Hardware Capability Management (`hardware.py`)
   - Model Selection & Ensemble (`selection.py`)

3. **Solution Execution** (`shared/execution.py`)
   - Safe code execution environment
   - Resource monitoring and limits
   - Performance metrics collection

4. **Learning System** (`learning/`)
   - Strategy optimization based on past performance
   - Performance metrics database
   - Failure analysis and adaptation

## Configuration Management

Configuration is layered to separate shared defaults from local settings:

### YAML Configuration (Shared Defaults)
- `config/models.yaml`: Model capabilities and default parameters
- `config/hardware.yaml`: Hardware profiles and capabilities
- `config/resources.yaml`: Resource limits and timeouts
- `config/cache.yaml`: Cache behavior settings

### Environment Configuration (Local Settings)
- API keys and credentials
- Hardware-specific settings
- Local preferences
- Debug settings

See `.env.example` for available environment variables.

## Core Components

### Shared Library (`shared/`)

#### Configuration (`config.py`)
- Loads and merges configuration from all sources
- Provides access to settings throughout the system

#### Error Handling (`errors.py`)
Base error hierarchy:
- `BaseError`
  - `ValidationError`
  - `ExecutionError`
  - `ProviderError`

#### Utilities (`utils.py`)
Core functionality including:
- Problem fetching and caching
- File management
- Session handling
- HTTP requests

#### Solution Management
- `execution.py`: Safe code execution
- `validator.py`: Solution validation
- `testing.py`: Solution testing framework

### Learning System (`learning/`)

The learning system optimizes solution strategies based on past performance:

- `database.py`: Performance metrics storage
- `optimizer.py`: Strategy selection and optimization
- `schema.sql`: Database schema

## Data Flow

1. Problem Input
   - Problem text fetched from AoC
   - Parsed into structured format
   - Test cases extracted

2. Solution Generation
   - Problem analyzed by LLM
   - Solution code generated
   - Validated against test cases

3. Solution Execution
   - Code executed in safe environment
   - Results validated
   - Performance metrics collected

4. Learning
   - Performance data stored
   - Strategies optimized
   - Future approach adjusted

## Development Guidelines

1. Configuration
   - Use YAML for shared defaults
   - Use .env for local/machine-specific settings
   - Keep sensitive data in .env

2. Error Handling
   - Use appropriate error types
   - Include context in error messages
   - Log errors appropriately

3. Testing
   - Write tests for new components
   - Use test fixtures
   - Check both success and failure cases
