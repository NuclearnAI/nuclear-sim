#!/bin/bash
# Launch interactive load following scenario

echo "⚡ Nuclear Plant Simulator - Interactive Load Following"
echo "======================================================"
echo ""
echo "This will start an interactive simulation of load following operations."
echo "Watch how the reactor adjusts to changing electrical demand."
echo ""

RUN_NAME="Interactive Load Following $(date +%Y%m%d_%H%M)"

echo "Starting load following simulation: $RUN_NAME"
echo ""
echo "⚡ This scenario demonstrates:"
echo "   • Dynamic power adjustments"
echo "   • Grid demand response"
echo "   • Automatic control systems"
echo ""

python nuclear_sim.py run load_following \
    --name "$RUN_NAME" \
    --description "Interactive load following scenario" \
    --tags "interactive,load_following,grid_response" \
    --duration 7200
