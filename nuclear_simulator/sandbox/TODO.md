
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



**High Priority**

- Add monitor to Graph class. Monitor should record all states
- LiquidVessels should set dP_dV from input pressure and volume.
- Make it easier to initialize edges with flows.


**Low Priority**

- Convert graph properties accessors to just attributes. @property\ndef x(self):... becomes self.x = ...
- Reorganize `plants` by component type: Nodes, Edges, Graphs.
- All mass edges should have momentum?
- Refactor all derivative variables, like dXdY to dX_dY to make it easier to read lowercase derivatives.
- Change all physics equations to take in MW not Rv


**Long Term**

- Use better physical equations for transport, material properties, and heat exchange.



