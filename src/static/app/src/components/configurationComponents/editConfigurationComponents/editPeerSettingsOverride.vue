<script setup lang="ts">
import LocaleText from "@/components/text/localeText.vue";
import { fetchPost } from "@/utilities/fetch.js"
import {onMounted, reactive, ref} from "vue";
const props = defineProps(['configuration'])
const saving = ref(false)
const overridePeerSettings = ref({...props.configuration.Info.OverridePeerSettings})
const edited = ref(false)
const errorMsg = ref("")

onMounted(() => {
	document.querySelectorAll("#editPeerSettingsOverride input").forEach(
		x => x.addEventListener("change", () => {
			edited.value = true
		})
	)
})

const resetForm = () => {
	overridePeerSettings.value = props.configuration.Info.OverridePeerSettings
	edited.value = false
}

const submitForm = async () => {
	document.querySelectorAll("#editPeerSettingsOverride input").forEach(
		x => x.classList.remove("is-invalid", "is-valid")
	)
	await fetchPost("/api/updateWireguardConfigurationInfo", {
		Name: props.configuration.Name,
		Key: "OverridePeerSettings",
		Value: overridePeerSettings.value
	}, (res) => {
		if (res.status){
			edited.value = false
			props.configuration.Info.OverridePeerSettings = overridePeerSettings.value
			document.querySelectorAll("#editPeerSettingsOverride input").forEach(
				x => x.classList.add("is-valid")
			)
		}else{
			errorMsg.value = res.message
			document.querySelector(`#override_${res.data}`).classList.add("is-invalid")
		}
	})
}
</script>

<template>
<div id="editPeerSettingsOverride">
	<h5 class="mb-0">
		<LocaleText t="Override Peer Settings"></LocaleText>
	</h5>
	<h6 class="mb-3 text-muted">
		<small>
			<LocaleText t="Only apply to peers in this configuration"></LocaleText>
		</small>
	</h6>
	<div class="d-flex gap-2 flex-column">
		<div>
			<label for="override_DNS" class="form-label">
				<small class="text-muted">
					<LocaleText t="DNS"></LocaleText>
				</small>
			</label>
			<input type="text" class="form-control form-control-sm rounded-3"
				   :disabled="saving"
				   v-model="overridePeerSettings.DNS"
				   id="override_DNS">
			<div class="invalid-feedback">{{ errorMsg }}</div>
		</div>
		<div>
			<label for="override_EndpointAllowedIPs" class="form-label">
				<small class="text-muted">
					<LocaleText t="Endpoint Allowed IPs"></LocaleText>
				</small>
			</label>
			<input type="text" class="form-control form-control-sm rounded-3"
				   :disabled="saving"
				   v-model="overridePeerSettings.EndpointAllowedIPs"
				   id="override_EndpointAllowedIPs">
			<div class="invalid-feedback">{{ errorMsg }}</div>
		</div>
		<div>
			<label for="override_ListenPort" class="form-label">
				<small class="text-muted">
					<LocaleText t="Listen Port"></LocaleText>
				</small>
			</label>
			<input type="text" class="form-control form-control-sm rounded-3"
				   :disabled="saving"
				   v-model="overridePeerSettings.ListenPort"
				   id="override_ListenPort">
			<div class="invalid-feedback">{{ errorMsg }}</div>
		</div>
		<div>
			<label for="override_MTU" class="form-label">
				<small class="text-muted">
					<LocaleText t="MTU"></LocaleText>
				</small>
			</label>
			<input type="text"
				   class="form-control form-control-sm rounded-3"
				   :disabled="saving"
				   v-model="overridePeerSettings.MTU"
				   id="override_MTU">
			<div class="invalid-feedback">{{ errorMsg }}</div>
		</div>
		<div>
			<label for="override_PeerRemoteEndpoint" class="form-label">
				<small class="text-muted">
					<LocaleText t="Peer Remote Endpoint"></LocaleText>
				</small>
			</label>
			<input type="text" class="form-control form-control-sm rounded-3"
				   :disabled="saving"
				   v-model="overridePeerSettings.PeerRemoteEndpoint"
				   id="override_PeerRemoteEndpoint">
		</div>
		<div>
			<label for="override_persistent_keepalive" class="form-label">
				<small class="text-muted">
					<LocaleText t="Persistent Keepalive"></LocaleText>
				</small>
			</label>
			<input type="text" class="form-control form-control-sm rounded-3"
				   :disabled="saving"
				   v-model="overridePeerSettings.PersistentKeepalive"
				   id="override_PersistentKeepalive">
			<div class="invalid-feedback">{{ errorMsg }}</div>
		</div>
		<div class="d-flex mt-1 gap-2">
			<button
				:class="{disabled: !edited}"
				@click="resetForm()"
				class="btn btn-sm bg-secondary-subtle border-secondary-subtle text-secondary-emphasis rounded-3 shadow ms-auto">
				<i class="bi bi-arrow-clockwise me-2"></i>
				<LocaleText t="Reset"></LocaleText>
			</button>
			<button
				:class="{disabled: !edited}"
				@click="submitForm()"
				class="btn btn-sm bg-primary-subtle border-primary-subtle text-primary-emphasis rounded-3 shadow">
				<i class="bi bi-save-fill me-2"></i>
				<LocaleText t="Save"></LocaleText>
			</button>
		</div>
	</div>
</div>
</template>

<style scoped>

</style>