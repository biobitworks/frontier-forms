// pi-computer-use with the macOS desktop backend turned off, for CDP browser pages only.
// The desktop backend needs a signed helper plus Accessibility and Screen Recording grants on the user's real
// session. Browser pages take a separate CDP path that needs neither, so the benchmark uses only that path.
import { currentPlatformBackend as backend } from "../../node_modules/@injaneity/pi-computer-use/src/platform/index.ts";
import computerUse from "../../node_modules/@injaneity/pi-computer-use/extensions/computer-use.ts";

const granted = { accessibility: true, screenRecording: true };
Object.assign(backend, {
	ensureReady: async () => ({ permissionStatus: granted, lastPermissionCheckAt: Date.now(), helperDiagnostics: undefined }),
	listRoots: async () => [],
	listApps: async () => [],
});

export default computerUse;
