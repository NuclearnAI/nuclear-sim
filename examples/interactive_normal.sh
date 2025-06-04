#!/bin/bash
# Launch interactive normal operation scenario

echo "🔬 Nuclear Plant Simulator - Interactive Normal Operation"
echo "========================================================="
echo ""
echo "This will start an interactive simulation of normal reactor operation."
echo "You can advance step-by-step and watch parameters in real-time."
echo ""

RUN_NAME="Interactive Normal Operation $(date +%Y%m%d_%H%M)"

echo "Starting interactive simulation: $RUN_NAME"
echo ""

python nuclear_sim.py run normal_operation \
    --name "$RUN_NAME" \
    --description "Interactive normal operation scenario" \
    --tags "interactive,normal,baseline" \
    --duration 600
