#!/bin/bash
# Launch interactive Loss of Coolant Accident (LOCA) scenario

echo "🚨 Nuclear Plant Simulator - Interactive LOCA Scenario"
echo "======================================================"
echo ""
echo "This will start an interactive simulation of a Loss of Coolant Accident."
echo "This is a serious emergency scenario - watch safety systems respond!"
echo ""

RUN_NAME="Interactive LOCA $(date +%Y%m%d_%H%M)"

echo "Starting LOCA simulation: $RUN_NAME"
echo ""
echo "🚨 CRITICAL SCENARIO - This demonstrates:"
echo "   • Emergency core cooling systems"
echo "   • Automatic reactor SCRAM"
echo "   • Safety system responses"
echo "   • Pressure and temperature transients"
echo ""
echo "⚠️  Monitor fuel temperature and coolant pressure closely!"
echo ""

python nuclear_sim.py run loss_of_coolant \
    --name "$RUN_NAME" \
    --description "Interactive Loss of Coolant Accident scenario" \
    --tags "interactive,emergency,loca,safety" \
    --duration 900
