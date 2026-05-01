#!/bin/bash

# 🔗 API Discovery & Auth Service - Quick Start Script
# This script sets up the entire service in minutes!

set -e

echo "🔗 API Discovery & Auth Service - Quick Start"
echo "=============================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3.11+ is installed
check_python() {
    print_status "Checking Python version..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
            print_success "Python $PYTHON_VERSION found"
            PYTHON_CMD="python3"
        else
            print_error "Python 3.11+ required, found $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3 not found. Please install Python 3.11+"
        exit 1
    fi
}

# Check if required tools are installed
check_dependencies() {
    print_status "Checking dependencies..."
    
    # Check for pip
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 not found. Please install pip3"
        exit 1
    fi
    
    # Check for git (optional)
    if ! command -v git &> /dev/null; then
        print_warning "git not found. Some features may not work"
    fi
    
    print_success "Dependencies check passed"
}

# Setup virtual environment
setup_venv() {
    print_status "Setting up virtual environment..."
    
    if [ ! -d "venv" ]; then
        $PYTHON_CMD -m venv venv
        print_success "Virtual environment created"
    else
        print_status "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    print_success "Virtual environment activated"
}

# Install dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    pip install --upgrade pip
    pip install -r requirements.txt
    
    print_success "Python dependencies installed"
    
    print_status "Installing Playwright browsers..."
    playwright install chromium --with-deps
    print_success "Playwright browsers installed"
}

# Setup environment variables
setup_env() {
    print_status "Setting up environment variables..."
    
    if [ ! -f ".env" ]; then
        cp .env.example .env
        print_success "Environment file created from template"
        
        echo ""
        print_warning "⚠️  REQUIRED API KEYS:"
        echo ""
        echo "   🔍 TAVILY_API_KEY (Required for API Discovery)"
        echo "      • Get from: https://tavily.com"
        echo "      • Purpose: AI-powered search to find relevant APIs"
        echo "      • Free tier: 1000 searches/month"
        echo ""
        echo "   🤖 OPENAI_API_KEY (Required for Browser Automation)"
        echo "      • Get from: https://openai.com"
        echo "      • Purpose: LLM processing for browser automation"
        echo "      • Used by browser-use for intelligent navigation"
        echo ""
        echo "   📝 Edit the .env file and add your API keys:"
        echo "      TAVILY_API_KEY=your_tavily_key_here"
        echo "      OPENAI_API_KEY=your_openai_key_here"
        echo ""
        
        # Check if API keys are set
        if grep -q "your_tavily_api_key_here" .env || grep -q "your_openai_api_key_here" .env; then
            print_error "Please configure your API keys in .env file first"
            echo ""
            echo "Steps to get API keys:"
            echo "1. Tavily API: Visit https://tavily.com → Sign up → Get API key"
            echo "2. OpenAI API: Visit https://openai.com → API → Create key"
            echo "3. Edit .env file with your keys"
            echo "4. Run this script again"
            exit 1
        else
            print_status "API keys appear to be configured"
        fi
    else
        print_status "Environment file already exists"
    fi
}

# Check API keys
check_api_keys() {
    print_status "Checking API keys..."
    
    source .env
    
    if [ -z "$TAVILY_API_KEY" ] || [ "$TAVILY_API_KEY" = "your_tavily_api_key_here" ]; then
        print_error "TAVILY_API_KEY not configured. Please set it in .env file"
        exit 1
    fi
    
    if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
        print_error "OPENAI_API_KEY not configured. Please set it in .env file"
        exit 1
    fi
    
    print_success "API keys configured"
}

# Start Redis (optional)
start_redis() {
    print_status "Checking Redis..."
    
    if command -v redis-server &> /dev/null; then
        if ! pgrep -x "redis-server" > /dev/null; then
            print_status "Starting Redis server..."
            redis-server --daemonize yes
            sleep 2
            print_success "Redis server started"
        else
            print_status "Redis server already running"
        fi
    else
        print_warning "Redis not found. Using in-memory cache instead"
        print_status "To install Redis: brew install redis (macOS) or apt-get install redis-server (Ubuntu)"
    fi
}

# Run tests
run_tests() {
    print_status "Running basic tests..."
    
    if [ -d "tests" ]; then
        python -m pytest tests/ -v --tb=short
        print_success "Tests passed"
    else
        print_warning "No tests found, skipping"
    fi
}

# Start the service
start_service() {
    print_status "Starting API Discovery Service..."
    
    echo ""
    print_success "🚀 Starting the service on http://localhost:8000"
    print_success "📖 API Documentation: http://localhost:8000/docs"
    print_success "🎮 Live Demo: http://localhost:8000"
    print_success "🏥 Health Check: http://localhost:8000/health"
    echo ""
    print_status "Press Ctrl+C to stop the service"
    echo ""
    
    # Start the service
    python -m gallely.api.main
}

# Main execution
main() {
    echo "This script will:"
    echo "1. Check Python and dependencies"
    echo "2. Set up virtual environment"
    echo "3. Install required packages"
    echo "4. Configure environment"
    echo "5. Start the service"
    echo ""
    
    read -p "Continue? (y/N): " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled"
        exit 0
    fi
    
    echo ""
    
    # Run setup steps
    check_python
    check_dependencies
    setup_venv
    install_dependencies
    setup_env
    check_api_keys
    start_redis
    run_tests
    
    echo ""
    print_success "✅ Setup complete!"
    echo ""
    
    # Ask if user wants to start the service
    read -p "Start the service now? (Y/n): " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        start_service
    else
        echo ""
        print_success "Setup complete! To start the service later, run:"
        echo "  source venv/bin/activate"
        echo "  python -m gallely.api.main"
        echo ""
    fi
}

# Run main function
main "$@" 