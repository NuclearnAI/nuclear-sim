#!/bin/bash
# Launch interactive emergency scenario (steam line break)

echo "⚠️  Nuclear Plant Simulator - Interactive Emergency Scenario"
echo "============================================================"
echo ""
echo "This will start an interactive simulation of a steam line break emergency."
echo "Watch how the reactor responds to the emergency and safety systems activate."
echo ""

RUN_NAME="Interactive Emergency $(date +%Y%m%d_%H%M)"

echo "Starting emergency simulation: $RUN_NAME"
echo ""
echo "⚠️  WARNING: This scenario includes emergency conditions!"
echo "   Monitor safety systems and reactor parameters closely."
echo ""

python nuclear_sim.py run steam_line_break \
    --name "$RUN_NAME" \
    --description "Interactive steam line break emergency scenario" \
    --tags "interactive,emergency,steam_line_break" \
    --duration 600
