<script>
import LocaleText from "@/components/text/localeText.vue";
import { fetchPost } from "@/utilities/fetch.js";
import { WireguardConfigurationsStore } from "@/stores/WireguardConfigurationsStore.js";

export default {
	name: "dashboardWarpSettings",
	components: { LocaleText },
	setup() {
		const wireguardConfigurationsStore = WireguardConfigurationsStore();
		return { wireguardConfigurationsStore };
	},
	data() {
		return {
			licenseKey: "",
			warpName: "warp0",
			selectedConfig: "",
			loadingCreate: false,
			loadingRotate: false,
			statusMsg: "",
			statusType: "success"
		};
	},
	methods: {
		async createWarp() {
			this.loadingCreate = true;
			this.statusMsg = "";
			try {
				const res = await fetchPost("/api/warp/createInterface", {
					licenseKey: this.licenseKey,
					warpName: this.warpName
				});
				this.statusMsg = res.message || (res.status ? "WARP Interface created." : "Failed to create WARP interface.");
				this.statusType = res.status ? "success" : "danger";
			} catch (e) {
				this.statusMsg = e.message;
				this.statusType = "danger";
			} finally {
				this.loadingCreate = false;
			}
		},
		async rotateConfig() {
			if (!this.selectedConfig) return;
			this.loadingRotate = true;
			this.statusMsg = "";
			try {
				const res = await fetchPost("/api/warp/rotateInterface", {
					configName: this.selectedConfig,
					warpName: this.warpName
				});
				this.statusMsg = res.message || (res.status ? "Interface routed to WARP." : "Failed to route interface.");
				this.statusType = res.status ? "success" : "danger";
			} catch (e) {
				this.statusMsg = e.message;
				this.statusType = "danger";
			} finally {
				this.loadingRotate = false;
			}
		}
	}
};
</script>

<template>
	<div class="card rounded-3 shadow-sm mb-3">
		<div class="card-header bg-transparent border-0 pt-4 px-4">
			<h5 class="card-title fw-bold">Cloudflare WARP Outband Route</h5>
		</div>
		<div class="card-body px-4 pb-4">
			<div v-if="statusMsg" :class="['alert', 'alert-' + statusType, 'mb-3']">
				{{ statusMsg }}
			</div>
			
			<div class="mb-4 border-bottom pb-4">
				<h6>Create WARP Interface (wgcf)</h6>
				<div class="mb-2">
					<label class="form-label text-muted"><small>WARP License Key (Optional)</small></label>
					<input type="text" class="form-control rounded-3" v-model="licenseKey" placeholder="Enter WARP / WARP+ Key">
				</div>
				<div class="mb-3">
					<label class="form-label text-muted"><small>WARP Interface Name</small></label>
					<input type="text" class="form-control rounded-3" v-model="warpName" placeholder="warp0">
				</div>
				<button class="btn btn-dark rounded-3" :disabled="loadingCreate" @click="createWarp">
					<span v-if="loadingCreate" class="spinner-border spinner-border-sm me-1"></span>
					Create WARP Interface
				</button>
			</div>

			<div>
				<h6>Route WireGuard Interface to WARP Outband</h6>
				<div class="mb-3">
					<label class="form-label text-muted"><small>Select Configuration / Interface</small></label>
					<select class="form-select rounded-3" v-model="selectedConfig">
						<option value="" disabled>Choose WireGuard interface</option>
						<option v-for="c in wireguardConfigurationsStore.configurations" :key="c.Name" :value="c.Name">
							{{ c.Name }} ({{ c.Address }})
						</option>
					</select>
				</div>
				<button class="btn btn-primary rounded-3" :disabled="loadingRotate || !selectedConfig" @click="rotateConfig">
					<span v-if="loadingRotate" class="spinner-border spinner-border-sm me-1"></span>
					Route Selected Interface via WARP
				</button>
			</div>
		</div>
	</div>
</template>
