<script>
import {parseCidr, containsCidr, mergeCidr, expandCidr} from "cidr-tools";
import '@/utilities/wireguard.js'
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";
import {parseInterface, parsePeers} from "@/utilities/parseConfigurationFile.js";
import {ref} from "vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {exp} from "qrcode/lib/core/galois-field.js";
import NewConfigurationTemplates from "@/components/newConfigurationComponents/newConfigurationTemplates.vue";

export default {
	name: "newConfiguration",
	components: {NewConfigurationTemplates, LocaleText},
	async setup(){
		const store = WireguardConfigurationsStore()
		const protocols = ref([])
		await fetchGet("/api/protocolsEnabled", {}, (res) => {
			protocols.value = res.data
		})
		const dashboardStore = DashboardConfigurationStore();
		
		return {store, protocols, dashboardStore}
	},
	data(){
		return {
			newConfiguration: {
				ConfigurationName: "",
				Address: "",
				ListenPort: "",
				PrivateKey: "",
				PublicKey: "",
				PresharedKey: "",
				PreUp: "",
				PreDown: "",
				PostUp: "",
				PostDown: "",
				Table: "",
				Protocol: "wg",
				Jc: 5,
				Jmin: 49,
				Jmax: 998,
				S1: 17,
				S2: 110,
				H1: 0,
				H2: 0,
				H3: 0,
				H4: 0
			},
			numberOfAvailableIPs: "0",
			error: false,
			errorMessage: "",
			success: false,
			loading: false,
			parseInterfaceResult: undefined,
			parsePeersResult: undefined
		}
	},
	created() {
		this.wireguardGenerateKeypair();
		let hValue = []
		while ([...new Set(hValue)].length !== 4){
			hValue = [this.rand(1, (2**31) - 1), this.rand(1, (2**31) - 1), this.rand(1, (2**31) - 1), this.rand(1, (2**31) - 1)]
		}
		this.newConfiguration.H1 = hValue[0]
		this.newConfiguration.H2 = hValue[1]
		this.newConfiguration.H3 = hValue[2]
		this.newConfiguration.H4 = hValue[3]
	},
	methods: {
		rand(min, max){
			return Math.floor(Math.random() * (max - min) + min);
		},
		wireguardGenerateKeypair(){
			const wg = window.wireguard.generateKeypair();
			this.newConfiguration.PrivateKey = wg.privateKey;
			this.newConfiguration.PublicKey = wg.publicKey;
			this.newConfiguration.PresharedKey = wg.presharedKey;
		},
		async saveNewConfiguration(){
			if (this.goodToSubmit){
				this.loading = true;
				await fetchPost("/api/addWireguardConfiguration", this.newConfiguration, async (res) => {
					if (res.status){
						this.success = true
						await this.store.getConfigurations()
						this.$router.push(`/configuration/${this.newConfiguration.ConfigurationName}/peers`)
					}else{
						this.error = true;
						this.errorMessage = res.message;
						document.querySelector(`#${res.data}`).classList.remove("is-valid")
						document.querySelector(`#${res.data}`).classList.add("is-invalid")
						this.loading = false;
					}
				})
			}
		},
		openFileUpload(){
			document.querySelector("#fileUpload").click();
		},
		readFile(e){
			const file = e.target.files[0];
			if (!file) return false;
			const reader = new FileReader();
			reader.onload = (evt) => {
				this.parseInterfaceResult = parseInterface(evt.target.result);
				this.parsePeersResult = parsePeers(evt.target.result);
				let appliedFields = 0;
				if (this.parseInterfaceResult){
					this.newConfiguration.ConfigurationName = file.name.replace('.conf', '')
					for (let i of Object.keys(this.parseInterfaceResult)){
						if (Object.keys(this.newConfiguration).includes(i)){
							this.newConfiguration[i] = this.parseInterfaceResult[i];
							appliedFields += 1;
						}
					}
				}
				if (appliedFields > 0){
					this.dashboardStore.newMessage("WGDashboard", `Parse successful! Updated ${appliedFields} field(s)`, "success")
				}else {
					this.dashboardStore.newMessage("WGDashboard", `Parse failed`, "danger")
				}
			};
			reader.readAsText(file);
		}
	},
	computed: {
		goodToSubmit(){
			let requirements = ["ConfigurationName", "Address", "ListenPort", "PrivateKey"]
			let elements = [...document.querySelectorAll("input[required]")];
			return requirements.find(x => {
				return this.newConfiguration[x].length === 0
			}) === undefined && elements.find(x => {
				return x.classList.contains("is-invalid")
			}) === undefined
		}
	},
	watch: {
		'newConfiguration.Address'(newVal){
			let ele = document.querySelector("#Address");
			if (ele){
				ele.classList.remove("is-invalid", "is-valid")
				try{
					this.numberOfAvailableIPs = 0
					newVal.replace(" ", "").split(",").forEach(x => {
						let p = parseCidr(x);
						let i = Number(p.end - p.start);
						this.numberOfAvailableIPs += i + 1;
					})
					ele.classList.add("is-valid")
				}catch (e) {
					console.log(e)
					this.numberOfAvailableIPs = "0";
					ele.classList.add("is-invalid")
				}
			}
		},
		'newConfiguration.ListenPort'(newVal){
			let ele = document.querySelector("#ListenPort");
			if (ele){
				ele.classList.remove("is-invalid", "is-valid")

				if (newVal < 0 || newVal > 65353 || !Number.isInteger(newVal)){
					ele.classList.add("is-invalid")
				}else{
					ele.classList.add("is-valid")
				}
			}
		},
		'newConfiguration.ConfigurationName'(newVal){
			let ele = document.querySelector("#ConfigurationName");
			if (ele){
				ele.classList.remove("is-invalid", "is-valid")
				if (!/^[a-zA-Z0-9_=+.-]{1,15}$/.test(newVal) || newVal.length === 0 || this.store.Configurations.find(x => x.Name === newVal)){
					ele.classList.add("is-invalid")
				}else{
					ele.classList.add("is-valid")
				}
			}
		},
		'newConfiguration.PrivateKey'(newVal){
			let ele = document.querySelector("#PrivateKey");
			if (ele){
				ele.classList.remove("is-invalid", "is-valid")

				try{
					wireguard.generatePublicKey(newVal)
					ele.classList.add("is-valid")
				}catch (e) {
					ele.classList.add("is-invalid")
				}
			}
		}
	},
	mounted() {
		const fileUpload = document.querySelector("#fileUpload");
		fileUpload.addEventListener("change", this.readFile, false)
	}
}
</script>

<template>
	<div class="mt-md-5 mt-3 text-body">
		<div class="container mb-4">
			<div class="mb-4 d-flex align-items-center gap-4 align-items-center">
				<RouterLink to="/"
				            class="btn btn-dark btn-brand p-2 shadow" style="border-radius: 100%">
					<h2 class="mb-0" style="line-height: 0">
						<i class="bi bi-arrow-left-circle"></i>
					</h2>
				</RouterLink>
				<h2 class="mb-0">
					<LocaleText t="New Configuration"></LocaleText>
				</h2>
				<div class="d-flex gap-2 ms-auto">
					<button class="titleBtn py-2 text-decoration-none btn text-primary-emphasis bg-primary-subtle rounded-3 border-1 border-primary-subtle"
					        @click="openFileUpload()"
					        type="button" aria-expanded="false">
						<i class="bi bi-upload me-2"></i>
						<LocaleText t="Open File"></LocaleText>
					</button>
					<input type="file" id="fileUpload" multiple class="d-none" accept="text/plain" />
				</div>
			</div>
			
			<form class="text-body d-flex flex-column gap-3"
				@submit="(e) => {e.preventDefault(); this.saveNewConfiguration();}"
			>
				<div class="card rounded-3 shadow">
					<div class="card-header">
						<LocaleText t="Protocol"></LocaleText>
					</div>
					<div class="card-body d-flex gap-2 protocolBtnGroup">
						<a 
							v-if="this.protocols.includes('wg')"
							@click="this.newConfiguration.Protocol = 'wg'"
							:class="{'opacity-50': this.newConfiguration.Protocol !== 'wg'}"
							class="btn btn-primary wireguardBg border-0 " style="flex-basis: 100%">
							<i class="bi bi-check-circle-fill me-2" v-if="this.newConfiguration.Protocol === 'wg'"></i>
							<i class="bi bi-circle me-2" v-else></i>
							<strong>
								WireGuard
							</strong>
						</a>
						<a
							@click="this.newConfiguration.Protocol = 'awg'"
							v-if="this.protocols.includes('awg')"
							:class="{'opacity-50': this.newConfiguration.Protocol !== 'awg'}"
							class="btn btn-primary amneziawgBg border-0" style="flex-basis: 100%">
							<i class="bi bi-check-circle-fill me-2" v-if="this.newConfiguration.Protocol === 'awg'"></i>
							<i class="bi bi-circle me-2" v-else></i>
							<strong>
								AmneziaWG
							</strong>
						</a>
					</div>
				</div>
				
				<div class="card rounded-3 shadow">
					<div class="card-header">
						<LocaleText t="Configuration Name"></LocaleText>
					</div>
					<div class="card-body">
						<input type="text" class="form-control" placeholder="ex. wg1" id="ConfigurationName" 
						       v-model="this.newConfiguration.ConfigurationName"
						       :disabled="this.loading"
						       required>
						<div class="invalid-feedback">
							<div v-if="this.error">{{this.errorMessage}}</div>
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
				</div>
				<div class="card rounded-3 shadow">
					<div class="card-header">
						<LocaleText t="Private Key"></LocaleText> & <LocaleText t="Public Key"></LocaleText>
					</div>
					<div class="card-body" style="font-family: var(--bs-font-monospace)">
						<div class="mb-2">
							<label class="text-muted fw-bold mb-1"><small>
								<LocaleText t="Private Key"></LocaleText>
							</small></label>
							<div class="input-group">
								<input type="text" class="form-control" id="PrivateKey" required
								       :disabled="this.loading"
								       v-model="this.newConfiguration.PrivateKey" disabled
								>
								<button class="btn btn-outline-primary" type="button"
								        title="Regenerate Private Key"
								        @click="wireguardGenerateKeypair()"
								>
									<i class="bi bi-arrow-repeat"></i>
								</button>
							</div>
						</div>
						<div>
							<label class="text-muted fw-bold mb-1"><small>
								<LocaleText t="Public Key"></LocaleText>
							</small></label>
							<input type="text" class="form-control" id="PublicKey"
							       v-model="this.newConfiguration.PublicKey" disabled
							>
						</div>
					</div>
				</div>
				<NewConfigurationTemplates
					@subnet="args => this.newConfiguration.Address = args"
					@port="args => this.newConfiguration.ListenPort = args"
				></NewConfigurationTemplates>
				<div class="card rounded-3 shadow">
					<div class="card-header">
						<LocaleText t="Listen Port"></LocaleText>
					</div>
					<div class="card-body">
						<input type="number" class="form-control" placeholder="0-65353" id="ListenPort" 
						       min="1"
						       max="65353"
						       v-model="this.newConfiguration.ListenPort"
						       :disabled="this.loading"
						       required>
						<div class="invalid-feedback">
							<div v-if="this.error">{{this.errorMessage}}</div>
							<div v-else>
								<LocaleText t="Invalid port"></LocaleText>
							</div>
						</div>
					</div>
				</div>
				<div class="card rounded-3 shadow">
					<div class="card-header d-flex align-items-center">
						<LocaleText t="IP Address/CIDR"></LocaleText>
						<span class="badge rounded-pill text-bg-success ms-auto"><LocaleText :t="numberOfAvailableIPs + ' Available IP Address'"></LocaleText></span>
					</div>
					<div class="card-body">
						<input type="text" class="form-control" 
						       placeholder="Ex: 10.0.0.1/24" id="Address" 
						       v-model="this.newConfiguration.Address"
						       :disabled="this.loading"
						       required>
						<div class="invalid-feedback">
							<div v-if="this.error">{{this.errorMessage}}</div>
							<div v-else>
								IP Address/CIDR is invalid
							</div>
							
						</div>
					</div>
				</div>
				
				<hr>
				<div class="accordion" id="newConfigurationOptionalAccordion">
					<div class="accordion-item">
						<h2 class="accordion-header">
							<button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#newConfigurationOptionalAccordionCollapse">
								<LocaleText t="Optional Settings"></LocaleText>
							</button>
						</h2>
						<div id="newConfigurationOptionalAccordionCollapse" 
						     class="accordion-collapse collapse" data-bs-parent="#newConfigurationOptionalAccordion">
							<div class="accordion-body d-flex flex-column gap-3">
								<div class="card rounded-3" v-for="key in ['Table', 'PreUp', 'PreDown', 'PostUp', 'PostDown']">
									<div class="card-header">{{ key }}</div>
									<div class="card-body">
										<input type="text" 
										       class="form-control font-monospace" :id="key" v-model="this.newConfiguration[key]">
									</div>
								</div>

								<div class="card rounded-3" 
								     v-if="this.newConfiguration.Protocol === 'awg'"
								     v-for="key in ['Jc', 'Jmin', 'Jmax', 'S1', 'S2', 'H1', 'H2', 'H3', 'H4']">
									<div class="card-header">{{ key }}</div>
									<div class="card-body">
										<input type="text"
										       class="form-control font-monospace" :id="key" v-model="this.newConfiguration[key]">
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
				<button class="btn btn-dark btn-brand rounded-3 px-3 py-2 shadow ms-auto"
				        :disabled="!this.goodToSubmit || this.loading || this.success">
					<span v-if="this.success" class="d-flex w-100">
						<LocaleText t="Success"></LocaleText>!
						 <i class="bi bi-check-circle-fill ms-2"></i>
					</span>
					<span v-else-if="!this.loading" class="d-flex w-100">
						<i class="bi bi-save-fill me-2"></i>
						<LocaleText t="Save"></LocaleText>
					</span>
					<span v-else class="d-flex w-100 align-items-center">
						<LocaleText t="Saving..."></LocaleText>
						<span class="ms-2 spinner-border spinner-border-sm" role="status">
						</span>
					</span>
				</button>
			</form>
		</div>
	</div>
</template>

<style scoped>
.protocolBtnGroup a{
	transition: all 0.2s ease-in-out;
}
</style>