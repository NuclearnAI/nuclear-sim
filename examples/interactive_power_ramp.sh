#!/bin/bash
# Launch interactive power ramp scenario

echo "📈 Nuclear Plant Simulator - Interactive Power Ramp"
echo "==================================================="
echo ""
echo "This will start an interactive simulation of reactor power changes."
echo "Watch how control systems manage power level adjustments."
echo ""

RUN_NAME="Interactive Power Ramp $(date +%Y%m%d_%H%M)"

echo "Starting power ramp simulation: $RUN_NAME"
echo ""
echo "📊 This scenario demonstrates:"
echo "   • Control rod movements"
echo "   • Power level changes"
echo "   • Temperature responses"
echo ""

python nuclear_sim.py run power_ramp_up \
    --name "$RUN_NAME" \
    --description "Interactive power ramp up scenario" \
    --tags "interactive,power_ramp,control" \
    --duration 1800
