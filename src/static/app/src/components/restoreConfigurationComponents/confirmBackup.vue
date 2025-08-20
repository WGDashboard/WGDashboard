<script setup>
import {computed, onMounted, reactive, ref, watch} from "vue";
import LocaleText from "@/components/text/localeText.vue";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import {parseCidr} from "cidr-tools";
import {fetchPost} from "@/utilities/fetch.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {useRouter} from "vue-router";
import ProtocolBadge from "@/components/protocolBadge.vue";


const props = defineProps({
	selectedConfigurationBackup: Object
})

const newConfiguration = reactive({
	ConfigurationName: props.selectedConfigurationBackup.filename.split("_")[0],
	Backup: props.selectedConfigurationBackup.filename,
	Protocol: props.selectedConfigurationBackup.protocol
})

const lineSplit = props.selectedConfigurationBackup.content.split("\n");

for(let line of lineSplit){
	if( line === "[Peer]") break
	if (line.length > 0){
		let l = line.replace(" = ", "=").split("=")
		if (l[0] === "ListenPort"){
			newConfiguration[l[0]] = parseInt(l[1])
		}else{
			newConfiguration[l[0]] = l[1]
		}
	}
}


const error = ref(false)
const loading = ref(false)
const errorMessage = ref("")
const store = WireguardConfigurationsStore()

const validateConfigurationName = computed(() => {
	return /^[a-zA-Z0-9_=+.-]{1,15}$/.test(newConfiguration.ConfigurationName) 
		&& newConfiguration.ConfigurationName.length > 0 
		&& !store.Configurations.find(x => x.Name === newConfiguration.ConfigurationName)
})

const validatePrivateKey = computed(() => {
	try{
		window.wireguard.generatePublicKey(newConfiguration.PrivateKey)
	}catch (e) {
		return false
	}
	return true
})

const validateListenPort = computed(() => {
	return newConfiguration.ListenPort > 0 
		&& newConfiguration.ListenPort <= 65353 
		&& Number.isInteger(newConfiguration.ListenPort) 
		&& !store.Configurations.find(x => parseInt(x.ListenPort) === newConfiguration.ListenPort)
})

const validateAddress = computed(() => {
	try{
		parseCidr(newConfiguration.Address)
		return true
	}catch (e){
		return false
	}
})

const validateForm = computed(() => {
	return validateAddress.value 
		&& validateListenPort.value 
		&& validatePrivateKey.value 
		&& validateConfigurationName.value
})
onMounted(() => {
	document.querySelector("main").scrollTo({
		top: 0,
		behavior: "smooth"
	})
	watch(() => validatePrivateKey, (newVal) => {
		if (newVal){
			newConfiguration.PublicKey = window.wireguard.generatePublicKey(newConfiguration.PrivateKey)
		}
	}, {
		immediate: true
	})
})
const availableIPAddress = computed(() => {
	let p;
	try{
		p = parseCidr(newConfiguration.Address);
	}catch (e){
		return 0;
	}
	return p.end - p.start
})
const peersCount = computed(() => {
	if (props.selectedConfigurationBackup.database){
		let l = props.selectedConfigurationBackup.databaseContent.split("\n")
		return l.filter(x => x.search(`INSERT INTO "${newConfiguration.ConfigurationName}"`) >= 0).length
	}
	return 0
})
const restrictedPeersCount = computed(() => {
	if (props.selectedConfigurationBackup.database){
		let l = props.selectedConfigurationBackup.databaseContent.split("\n")
		return l.filter(x => x.search(`INSERT INTO "${newConfiguration.ConfigurationName}_restrict_access"`) >= 0).length
	}
	return 0
})
const dashboardStore = DashboardConfigurationStore()
const router = useRouter();
const submitRestore = async () => {
	if (validateForm.value){
		loading.value = true;
		await fetchPost("/api/addWireguardConfiguration", newConfiguration, async (res) => {
			if (res.status){
				dashboardStore.newMessage("Server", "Configuration restored", "success")
				await store.getConfigurations()
				await router.push(`/configuration/${newConfiguration.ConfigurationName}/peers`)
			}else{
				loading.value = false;
			}
		})
	}
}
</script>

<template>
<div class="d-flex flex-column gap-5" id="confirmBackup">
	<form class="d-flex flex-column gap-3">
		<div class="d-flex flex-column flex-sm-row align-items-start align-items-sm-center gap-3">
			<h4 class="mb-0">
				<LocaleText t="Configuration"></LocaleText>
			</h4>
		</div>
		<div>
			<label class="text-muted mb-1">
				<small>
					<LocaleText t="Protocol"></LocaleText>
				</small>
			</label>
			<h5 class="mb-0">
				<ProtocolBadge :protocol="selectedConfigurationBackup.protocol" :mini="true"></ProtocolBadge>
			</h5>
		</div>
		<div>
			<label class="text-muted mb-1" for="ConfigurationName"><small>
				<LocaleText t="Configuration Name"></LocaleText>
			</small></label>
			<input type="text" class="form-control rounded-3" placeholder="ex. wg1" id="ConfigurationName"
			       v-model="newConfiguration.ConfigurationName"
			       :class="[validateConfigurationName ? 'is-valid':'is-invalid']"
			       disabled
			       required>
			<div class="invalid-feedback">
				<div v-if="error">{{errorMessage}}</div>
				<div v-else>
					<LocaleText t="Configuration name is invalid. Possible reasons:"></LocaleText>
					<ul class="mb-0">
						<li>
							<LocaleText t="Configuration name already exist."></LocaleText>
						</li>
						<li>
							<LocaleText t="Configuration name can only contain 15 lower/uppercase alphabet, numbers, underscore, equal sign, plus sign, period and hyphen."></LocaleText>
						</li>
					</ul>
				</div>
			</div>
		</div>
		<div class="row g-3">
			<div class="col-sm">
				<div>
					<label class="text-muted mb-1" for="PrivateKey"><small>
						<LocaleText t="Private Key"></LocaleText>
					</small></label>
					<div class="input-group">
						<input type="text" class="form-control rounded-start-3" id="PrivateKey" required
						       :class="[validatePrivateKey ? 'is-valid':'is-invalid']"
						       v-model="newConfiguration.PrivateKey" disabled
						>
					</div>
				</div>
			</div>
			<div class="col-sm">
				<div>
					<label class="text-muted mb-1" for="PublicKey"><small>
						<LocaleText t="Public Key"></LocaleText>
					</small></label>
					<input type="text" class="form-control rounded-3" id="PublicKey"
					       v-model="newConfiguration.PublicKey" disabled
					>
				</div>
			</div>
		</div>
		<div>
			<label class="text-muted mb-1" for="ListenPort"><small>
				<LocaleText t="Listen Port"></LocaleText>
			</small></label>
			<input type="number" class="form-control rounded-3" placeholder="0-65353" id="ListenPort"
			       min="1"
			       max="65353"
			       v-model="newConfiguration.ListenPort"
			       :class="[validateListenPort ? 'is-valid':'is-invalid']"
			       disabled
			       required>
			<div class="invalid-feedback">
				<div v-if="error">{{errorMessage}}</div>
				<div v-else>
					<LocaleText t="Listen Port is invalid. Possible reasons:"></LocaleText>
					<ul class="mb-0">
						<li>
							<LocaleText t="Invalid port."></LocaleText>
						</li>
						<li>
							<LocaleText t="Port is assigned to existing WireGuard Configuration."></LocaleText>
						</li>
					</ul>
				</div>
			</div>
		</div>
		<div>
			<label class="text-muted mb-1 d-flex" for="ListenPort">
				<small>
					<LocaleText t="IP Address/CIDR"></LocaleText>
				</small>
				<small class="ms-auto" :class="[availableIPAddress > 0 ? 'text-success':'text-danger']">
					<LocaleText :t="availableIPAddress + ' Available IP Address'"></LocaleText>
				</small>
			</label>
			<input type="text" class="form-control"
			       placeholder="Ex: 10.0.0.1/24" id="Address"
			       v-model="newConfiguration.Address"
			       :class="[validateAddress ? 'is-valid':'is-invalid']"
			       disabled
			       required>
			<div class="invalid-feedback">
				<div v-if="error">{{errorMessage}}</div>
				<div v-else>
					<LocaleText t="IP Address/CIDR is invalid"></LocaleText>
				</div>
			</div>
		</div>
		<div class="accordion" id="newConfigurationOptionalAccordion">
			<div class="accordion-item">
				<h2 class="accordion-header">
					<button class="accordion-button collapsed rounded-3" 
					        type="button" data-bs-toggle="collapse" data-bs-target="#newConfigurationOptionalAccordionCollapse">
						<LocaleText t="Optional Settings"></LocaleText>
					</button>
				</h2>
				<div id="newConfigurationOptionalAccordionCollapse"
				     class="accordion-collapse collapse " 
				     data-bs-parent="#newConfigurationOptionalAccordion">
					<div class="accordion-body d-flex flex-column gap-3">
						<div>
							<label class="text-muted mb-1" for="PreUp"><small>
								<LocaleText t="PreUp"></LocaleText>
							</small></label>
							<input type="text" class="form-control rounded-3" id="PreUp"
							       disabled
							       v-model="newConfiguration.PreUp">
						</div>
						<div>
							<label class="text-muted mb-1" for="PreDown"><small>
								<LocaleText t="PreDown"></LocaleText>
							</small></label>
							<input type="text" class="form-control rounded-3" id="PreDown"
							       disabled
							       v-model="newConfiguration.PreDown">
						</div>
						<div>
							<label class="text-muted mb-1" for="PostUp"><small>
								<LocaleText t="PostUp"></LocaleText>
							</small></label>
							<input type="text" class="form-control rounded-3" id="PostUp"
							       disabled
							       v-model="newConfiguration.PostUp">
						</div>
						<div>
							<label class="text-muted mb-1" for="PostDown"><small>
								<LocaleText t="PostDown"></LocaleText>
							</small></label>
							<input type="text" class="form-control rounded-3" id="PostDown"
							       disabled
							       v-model="newConfiguration.PostDown">
						</div>
					</div>
				</div>
			</div>
		</div>
	</form>
	<div class="d-flex flex-column gap-3">
		<div class="d-flex flex-column flex-sm-row align-items-start align-items-sm-center gap-3">
			<h4 class="mb-0">
				<LocaleText t="Database File"></LocaleText>
			</h4>
			<h4 class="mb-0 ms-auto" :class="[selectedConfigurationBackup.database ? 'text-success':'text-danger']">
				<i class="bi" :class="[selectedConfigurationBackup.database ? 'bi-check-circle-fill':'bi-x-circle-fill']"></i>
			</h4>
		</div>
		<div v-if="selectedConfigurationBackup.database">
			<div class="row g-3">
				<div class="col-sm">
					<div class="card text-bg-success rounded-3">
						<div class="card-body">
							<i class="bi bi-person-fill me-2"></i>
							<LocaleText t="Contain"></LocaleText> <strong>{{peersCount}}</strong> <LocaleText t="Peer" v-if="peersCount > 1"></LocaleText><LocaleText t="Peer" v-else></LocaleText>
						</div>
					</div>
				</div>
				<div class="col-sm">
					<div class="card text-bg-warning rounded-3">
						<div class="card-body">
							<i class="bi bi-person-fill-lock me-2"></i>
							<LocaleText t="Contain"></LocaleText> <strong>{{restrictedPeersCount}}</strong> <LocaleText t="Restricted Peers" v-if="restrictedPeersCount > 1" /><LocaleText t="Restricted Peers" v-else></LocaleText>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
<!--	TODO: Fix loading state, same with bulk delete-->
	<div class="d-flex">
		<button class="btn btn-dark btn-brand rounded-3 px-3 py-2 shadow ms-auto"
			:disabled="!validateForm || loading"
		        @click="submitRestore()"
		>
			<i class="bi bi-clock-history me-2"></i>
			<LocaleText :t="!loading ? 'Restore':'Restoring...'"></LocaleText>
		</button>
	</div>
</div>
</template>

<style scoped>

</style>