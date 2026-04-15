# Phase 9: OpenUSD Export

Due to the extreme complexity of the combined macro anatomy (entire cerebral and spinal CSF cavities) and micro anatomy (millions of trabeculae struts), standard OBJ/STL exports become cumbersome. 

We export to **OpenUSD** using the Pixar `pxr` Python libs. 

This enables:
1. Highly efficient instantiation of trabecular geometries.
2. Semantic labeling (e.g. tagging specific cisterns, ventricles).
3. Ready-for-Unity / Omniverse integration for the WebGL viewer and MIME testing.

See `docs/openusd-compatibility.md` for architecture specifics.
