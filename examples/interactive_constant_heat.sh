#!/bin/bash
# Launch interactive constant heat source demo

echo "🔧 Nuclear Plant Simulator - Interactive Constant Heat Source Demo"
echo "=================================================================="
echo ""
echo "This will start an interactive demonstration of the decoupled architecture"
echo "using a constant heat source. Perfect for testing secondary side systems"
echo "without reactor physics complexity!"
echo ""

RUN_NAME="Interactive Constant Heat Demo $(date +%Y%m%d_%H%M)"

echo "Starting constant heat demo: $RUN_NAME"
echo ""
echo "🔧 This demo demonstrates:"
echo "   • Instant heat source response"
echo "   • Independent power control"
echo "   • Grid demand simulation"
echo "   • Automatic demand following"
echo "   • Secondary side dynamics"
echo ""

# Option 1: Run the interactive Python demo directly
echo "Running interactive constant heat source demo..."
python examples/interactive_constant_heat.py

echo ""
echo "Demo completed! You can also run simulations with:"
echo "python nuclear_sim.py run normal_operation --name \"$RUN_NAME\" --heat-source constant --duration 300"
