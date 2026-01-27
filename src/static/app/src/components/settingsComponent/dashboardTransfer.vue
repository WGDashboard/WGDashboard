<script setup>
import {onMounted, ref} from "vue";
import LocaleText from "@/components/text/localeText.vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {fetchGet, fetchPost, getUrl} from "@/utilities/fetch.js";

const store = DashboardConfigurationStore();

const exporting = ref(false);
const importing = ref(false);

const includeDashboardConfig = ref(false);
const includeWireguardConfigs = ref(true);
const includeAmneziaConfigs = ref(true);

const applyDashboardConfig = ref(false);
const importWireguardConfigs = ref(true);
const importAmneziaConfigs = ref(true);
const amneziaAvailable = ref(true);

const importFile = ref(null);
const importFileName = ref("");

const onFileChange = (event) => {
	const file = event.target.files[0];
	importFile.value = file || null;
	importFileName.value = file ? file.name : "";
};

onMounted(async () => {
	await fetchGet("/api/protocolsEnabled", {}, (res) => {
		if (res.status){
			const protocols = res.data || [];
			amneziaAvailable.value = protocols.includes("awg");
			if (!amneziaAvailable.value){
				includeAmneziaConfigs.value = false;
				importAmneziaConfigs.value = false;
			}
		}
	});
});

const exportTransfer = async () => {
	exporting.value = true;
	await fetchPost("/api/transfer/export", {
		includeDashboardConfig: includeDashboardConfig.value,
		includeWireguardConfigs: includeWireguardConfigs.value,
		includeAmneziaConfigs: includeAmneziaConfigs.value
	}, (res) => {
		if (res.status){
			window.open(getUrl(`/fileDownload?file=${res.data}`), "_blank");
			store.newMessage("Server", "Transfer export created", "success");
		}else{
			store.newMessage("Server", res.message || "Export failed", "danger");
		}
	});
	exporting.value = false;
};

const importTransfer = async () => {
	if (!importFile.value){
		store.newMessage("Server", "Please select a transfer file", "warning");
		return;
	}
	importing.value = true;
	const reader = new FileReader();
	reader.onload = async () => {
		await fetchPost("/api/transfer/import", {
			file: reader.result,
			applyDashboardConfig: applyDashboardConfig.value,
			importWireguardConfigs: importWireguardConfigs.value,
			importAmneziaConfigs: importAmneziaConfigs.value
		}, (res) => {
			if (res.status){
				store.newMessage("Server", res.message || "Import completed", "success");
			}else{
				store.newMessage("Server", res.message || "Import failed", "danger");
			}
		});
		importing.value = false;
	};
	reader.onerror = () => {
		store.newMessage("Server", "Failed to read file", "danger");
		importing.value = false;
	};
	reader.readAsDataURL(importFile.value);
};
</script>

<template>
	<div class="card rounded-3">
		<div class="card-header">
			<h6 class="my-2">
				<i class="bi bi-arrow-left-right me-2"></i>
				<LocaleText t="Dashboard Transfer"></LocaleText>
			</h6>
		</div>
		<div class="card-body d-flex flex-column gap-3">
			<div>
				<h6 class="mb-1">
					<LocaleText t="Export Transfer File"></LocaleText>
				</h6>
				<p class="text-muted small mb-2">
					<LocaleText t="Export includes database and selected configuration files."></LocaleText>
				</p>
				<div class="form-check form-switch mb-2">
					<input class="form-check-input" type="checkbox" role="switch"
						   v-model="includeDashboardConfig" id="includeDashboardConfig">
					<label class="form-check-label" for="includeDashboardConfig">
						<LocaleText t="Include WGDashboard Config"></LocaleText>
					</label>
				</div>
				<div class="form-check form-switch mb-2">
					<input class="form-check-input" type="checkbox" role="switch"
						   v-model="includeWireguardConfigs" id="includeWireguardConfigs">
					<label class="form-check-label" for="includeWireguardConfigs">
						<LocaleText t="Include WireGuard Configurations"></LocaleText>
					</label>
				</div>
				<div class="form-check form-switch mb-3">
					<input class="form-check-input" type="checkbox" role="switch"
						   v-model="includeAmneziaConfigs" id="includeAmneziaConfigs"
						   :disabled="!amneziaAvailable">
					<label class="form-check-label" for="includeAmneziaConfigs">
						<LocaleText t="Include AmneziaWG Configurations"></LocaleText>
					</label>
				</div>
				<button class="btn btn-sm btn-outline-primary" @click="exportTransfer" :disabled="exporting">
					<i class="bi bi-download me-2"></i>
					<LocaleText :t="exporting ? 'Exporting...' : 'Export'"></LocaleText>
				</button>
			</div>
			<hr>
			<div>
				<h6 class="mb-1">
					<LocaleText t="Import Transfer File"></LocaleText>
				</h6>
				<p class="text-muted small mb-2">
					<LocaleText t="Import will overwrite existing data."></LocaleText>
				</p>
				<div class="mb-2">
					<label class="form-label">
						<LocaleText t="Select a transfer file (.zip)"></LocaleText>
					</label>
					<input class="form-control" type="file" accept=".zip" @change="onFileChange">
					<div class="text-muted small mt-1" v-if="importFileName">
						{{ importFileName }}
					</div>
				</div>
				<div class="form-check form-switch mb-2">
					<input class="form-check-input" type="checkbox" role="switch"
						   v-model="applyDashboardConfig" id="applyDashboardConfig">
					<label class="form-check-label" for="applyDashboardConfig">
						<LocaleText t="Apply WGDashboard Config on Import"></LocaleText>
					</label>
				</div>
				<div class="form-check form-switch mb-2">
					<input class="form-check-input" type="checkbox" role="switch"
						   v-model="importWireguardConfigs" id="importWireguardConfigs">
					<label class="form-check-label" for="importWireguardConfigs">
						<LocaleText t="Import WireGuard Configurations"></LocaleText>
					</label>
				</div>
				<div class="form-check form-switch mb-3">
					<input class="form-check-input" type="checkbox" role="switch"
						   v-model="importAmneziaConfigs" id="importAmneziaConfigs"
						   :disabled="!amneziaAvailable">
					<label class="form-check-label" for="importAmneziaConfigs">
						<LocaleText t="Import AmneziaWG Configurations"></LocaleText>
					</label>
				</div>
				<button class="btn btn-sm btn-outline-danger" @click="importTransfer" :disabled="importing">
					<i class="bi bi-upload me-2"></i>
					<LocaleText :t="importing ? 'Importing...' : 'Import'"></LocaleText>
				</button>
			</div>
		</div>
	</div>
</template>
