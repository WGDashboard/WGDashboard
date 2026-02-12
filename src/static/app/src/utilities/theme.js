import {ref} from "vue";

const prefersDark = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
export const systemTheme = ref(prefersDark && prefersDark.matches ? "dark" : "light");

let watcherInitialized = false;

export function initSystemThemeWatcher() {
	if (watcherInitialized || !prefersDark) return;
	watcherInitialized = true;
	const handler = (event) => {
		systemTheme.value = event.matches ? "dark" : "light";
	};
	if (prefersDark.addEventListener) {
		prefersDark.addEventListener("change", handler);
	} else if (prefersDark.addListener) {
		prefersDark.addListener(handler);
	}
}

export function resolveTheme(theme) {
	if (theme === "system") return systemTheme.value;
	if (theme === "dark" || theme === "light") return theme;
	return "dark";
}
