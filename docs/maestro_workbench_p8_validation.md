# Maestro Workbench P8 validation notes

## Physical-device acceptance

On 2026-08-15, the P8/P8.1 Guided Study Builder completed its physical-device acceptance flow on an iPhone over trusted-LAN HTTP using the Narrative Competition Smoke Test fixture. Step 7 returned `VALID`, Guided-to-Advanced handoff preserved the draft, and Advanced Protocol Editor validation returned `Draft valid. Review is available. No write occurred.` No Study was registered.

## Runtime identity guardrail

The Workbench now publishes and displays the serving process ID, Python executable, backend module path, static root, package version, launch mode, research schema version, Study-registration-contract SHA-256, Studies-asset SHA-256, and required Study-contract capabilities. Study creation and registration fail closed when the runtime identity endpoint is absent or lacks the required P7/E1 contract capabilities. Startup reports the same identity, and an occupied port produces an explicit stale-listener warning.
