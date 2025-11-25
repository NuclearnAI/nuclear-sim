
# TODO

Todo list and statuses for the nuclear powerplant simulation code.

**Primary goal**  
Simulate nuclear powerplant using modular, scalable, and easy-to-understand code.

## Status

The status of each module

**graphs**  
Graphs is essentially complete. It should not require much additional edits.

**materials**  
Materials is on a solid foundation. The base is good and hopefully the only things needed moving forward are defining materials and adding minor new properties (like phase transitions) to different materials.

**physics**  
Physics is continuously updated, yet simultaneously low maintenance. The module only defines constants and functions, meaning that there should never be any major changes to the module aside from reorganizing folders or names.

**plants**  
Plants is in alpha version. Anything in the module can be changed.

## Tasks


**Immediate**

- Change LiquidVessel to PressurizedVessel
  - node.liquid -> node.material
  - properties for gas, liquid, solid
- Split GasLiquidVessel into Graph with Gas and Liquid nodes.
- Remove Hot and Cold leg from Steam generator primary.
  - Rename Drum and Bundle?


**High Priority**



**Low Priority**

- Convert graph properties accessors to just attributes. @property\ndef x(self):... becomes self.x = ...
- Reorganize `plants` by component type: Nodes, Edges, Graphs.
- All mass edges should have momentum?
- Refactor all derivative variables, like dXdY to dX_dY to make it easier to read lowercase derivatives.
- Change all physics equations to take in MW not Rv

- Convert pipe diameter fields to pipe area fields. No sense in recalculating area every time.


**Long Term**

- Use better physical equations for transport, material properties, and heat exchange.



