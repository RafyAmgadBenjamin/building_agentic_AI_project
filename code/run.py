import os
import sys
import argparse

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Run Perplexia AI Assistant')
parser.add_argument('--week', type=str, choices=['project'], default='project', 
                    help="type project to be able to run the project ('project')")
parser.add_argument('--mode', type=str, choices=['part1', 'part2', 'part3'], 
                    default='part1', help='Which part of the selected week to run')
parser.add_argument('--solution', action='store_true',
                    help='Run solution code instead of student code')
args = parser.parse_args()

# Import and run the app
from perplexia_ai.app import create_demo

if __name__ == "__main__":
    # Convert week to int if it's '1', '2', or '3', else keep as string
    week = args.week
    
    demo = create_demo(week=week, mode_str=args.mode, use_solution=args.solution)
    demo.launch()