<script>
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import NameInput from "@/components/configurationComponents/newPeersComponents/nameInput.vue";
import PrivatePublicKeyInput from "@/components/configurationComponents/newPeersComponents/privatePublicKeyInput.vue";
import AllowedIPsInput from "@/components/configurationComponents/newPeersComponents/allowedIPsInput.vue";
import DnsInput from "@/components/configurationComponents/newPeersComponents/dnsInput.vue";
import EndpointAllowedIps from "@/components/configurationComponents/newPeersComponents/endpointAllowedIps.vue";
import PresharedKeyInput from "@/components/configurationComponents/newPeersComponents/presharedKeyInput.vue";
import MtuInput from "@/components/configurationComponents/newPeersComponents/mtuInput.vue";
import PersistentKeepAliveInput
	from "@/components/configurationComponents/newPeersComponents/persistentKeepAliveInput.vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import BulkAdd from "@/components/configurationComponents/newPeersComponents/bulkAdd.vue";
import LocaleText from "@/components/text/localeText.vue";

export default {
	name: "peerCreate",
	components: {
		LocaleText,
		BulkAdd,
		PersistentKeepAliveInput,
		MtuInput,
		PresharedKeyInput, EndpointAllowedIps, DnsInput, AllowedIPsInput, PrivatePublicKeyInput, NameInput},
	data(){
		return{
			data: {
				bulkAdd: false,
				bulkAddAmount: 0,
				name: "",
				allowed_ips: [],
				private_key: "",
				public_key: "",
				DNS: this.dashboardStore.Configuration.Peers.peer_global_dns,
				endpoint_allowed_ip: this.dashboardStore.Configuration.Peers.peer_endpoint_allowed_ip,
				keepalive: parseInt(this.dashboardStore.Configuration.Peers.peer_keep_alive),
				mtu: parseInt(this.dashboardStore.Configuration.Peers.peer_mtu),
				preshared_key: "",
				preshared_key_bulkAdd: false,
				advanced_security: "off",
			},
			availableIp: undefined,
			availableIpSearchString: "",
			saving: false,
			allowedIpDropdown: undefined
		}
	},
	mounted() {
		fetchGet("/api/getAvailableIPs/" + this.$route.params.id, {}, (res) => {
			if (res.status){
				this.availableIp = res.data;
			}
		})
	},
	setup(){
		const store = WireguardConfigurationsStore();
		const dashboardStore = DashboardConfigurationStore();
		return {store, dashboardStore}
	}, 
	methods: {
		peerCreate(){
			this.saving = true
			fetchPost("/api/addPeers/" + this.$route.params.id, this.data, (res) => {
				if (res.status){
					this.$router.push(`/configuration/${this.$route.params.id}/peers`)
					this.dashboardStore.newMessage("Server", "Peer created successfully", "success")
				}else{
					this.dashboardStore.newMessage("Server", res.message, "danger")
				}
				this.saving = false;
			})
		}	
	},
	computed:{
		allRequireFieldsFilled(){
			let status = true;
			if (this.data.bulkAdd){
				if(this.data.bulkAddAmount.length === 0 || this.data.bulkAddAmount > this.availableIp.length){
					status = false;
				}
			}else{
				let requireFields =
					["allowed_ips", "private_key", "public_key", "endpoint_allowed_ip", "keepalive", "mtu"]
				requireFields.forEach(x => {
					if (this.data[x].length === 0) status = false;
				});
			}
			return status;
		},
		getProtocol(){
			return this.store.Configurations.find(x => x.Name === this.$route.params.id).Protocol;
		}
	},
	watch: {
		bulkAdd(newVal){
			if(!newVal){
				this.data.bulkAddAmount = "";
			}
		},
		'data.bulkAddAmount'(){
			if (this.data.bulkAddAmount > this.availableIp.length){
				this.data.bulkAddAmount = this.availableIp.length;
			}
		}
	}
}
</script>

<template>
	<div class="container">
		<div class="mb-4">
			<div class="mb-5 d-flex align-items-center gap-4">
				<RouterLink to="peers"
				            class="btn btn-dark btn-brand p-2 shadow" style="border-radius: 100%">
					<h2 class="mb-0" style="line-height: 0">
						<i class="bi bi-arrow-left-circle"></i>
					</h2>
				</RouterLink>
				<h2 class="mb-0">
					<LocaleText t="Add Peers"></LocaleText>
				</h2>
			</div>
			
		</div>
		<div class="d-flex flex-column gap-2">
			<BulkAdd :saving="saving" :data="this.data" :availableIp="this.availableIp"></BulkAdd>
			<hr class="mb-0 mt-2">
			<NameInput :saving="saving" :data="this.data" v-if="!this.data.bulkAdd"></NameInput>
			<PrivatePublicKeyInput :saving="saving" :data="data" v-if="!this.data.bulkAdd"></PrivatePublicKeyInput>
			<AllowedIPsInput :availableIp="this.availableIp" :saving="saving" :data="data" v-if="!this.data.bulkAdd"></AllowedIPsInput>
			<EndpointAllowedIps :saving="saving" :data="data"></EndpointAllowedIps>
			<DnsInput :saving="saving" :data="data"></DnsInput>

			<hr class="mb-0 mt-2">
			<div class="row gy-3">
				<div class="col-sm" v-if="!this.data.bulkAdd">
					<PresharedKeyInput :saving="saving" :data="data" :bulk="this.data.bulkAdd"></PresharedKeyInput>
				</div>
				
				<div class="col-sm">
					<MtuInput :saving="saving" :data="data"></MtuInput>
				</div>
				<div class="col-sm">
					<PersistentKeepAliveInput :saving="saving" :data="data"></PersistentKeepAliveInput>
				</div>
				<div class="col-12" v-if="this.data.bulkAdd">
					<div class="form-check form-switch">
						<input class="form-check-input" type="checkbox" role="switch"
						       v-model="this.data.preshared_key_bulkAdd"
						       id="bullAdd_PresharedKey_Switch" checked>
						<label class="form-check-label" for="bullAdd_PresharedKey_Switch">
							<small class="fw-bold">
								<LocaleText t="Pre-Shared Key"></LocaleText> <LocaleText t="Enabled" v-if="this.data.preshared_key_bulkAdd"></LocaleText><LocaleText t="Disabled" v-else></LocaleText>
							</small>
						</label>
					</div>
				</div>
			</div>
			<hr>
			<div class="d-flex mt-2">
				<button class="ms-auto btn btn-dark btn-brand rounded-3 px-3 py-2 shadow"
				        :disabled="!this.allRequireFieldsFilled || this.saving"
				        @click="this.peerCreate()"
				>
					<i class="bi bi-plus-circle-fill me-2" v-if="!this.saving"></i>
					<LocaleText t="Adding..." v-if="this.saving"></LocaleText>
					<LocaleText t="Add" v-else></LocaleText>
				</button>
			</div>
		</div>
	</div>
</template>

<style scoped>
.peerSettingContainer {
	background-color: #00000060;
	z-index: 9998;
}

div{
	transition: 0.2s ease-in-out;
}

.inactiveField{
	opacity: 0.4;
}

.card{
	max-height: 100%;
}
</style>