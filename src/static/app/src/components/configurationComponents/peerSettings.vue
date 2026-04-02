<script>
import {fetchPost} from "@/utilities/fetch.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import LocaleText from "@/components/text/localeText.vue";

export default {
	name: "peerSettings",
	components: {LocaleText},
	props: {
		selectedPeer: Object
	},
	data(){
		return {
			data: undefined,
			dataChanged: false,
			showKey: false,
			saving: false
		}
	},
	setup(){
		const dashboardConfigurationStore = DashboardConfigurationStore();
		return {dashboardConfigurationStore}
	},
	methods: {
		reset(){
			if (this.selectedPeer){
				this.data = JSON.parse(JSON.stringify(this.selectedPeer))
				this.dataChanged = false;
			}
		},
		savePeer(){
			this.saving = true;
			fetchPost(`/api/updatePeerSettings/${this.$route.params.id}`, this.data, (res) => {
				this.saving = false;
				if (res.status){
					this.dashboardConfigurationStore.newMessage("Server", "Peer saved", "success")
				}else{
					this.dashboardConfigurationStore.newMessage("Server", res.message, "danger")
				}
				this.$emit("refresh")
			})
		},
		resetPeerData(type){
			this.saving = true
			fetchPost(`/api/resetPeerData/${this.$route.params.id}`, {
				id: this.data.id,
				type: type
			}, (res) => {
				this.saving = false;
				if (res.status){
					this.dashboardConfigurationStore.newMessage("Server", "Peer data usage reset successfully", "success")
				}else{
					this.dashboardConfigurationStore.newMessage("Server", res.message, "danger")
				}
				this.$emit("refresh")
			})
		}
	},
	beforeMount() {
		this.reset();
	},
	mounted() {
		this.$el.querySelectorAll("input").forEach(x => {
			x.addEventListener("change", () => {
				this.dataChanged = true;
			});
		})
	}
}
</script>

<template>
	<div class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0 overflow-y-scroll">
		<div class="container d-flex h-100 w-100">
			<div class="m-auto modal-dialog-centered dashboardModal">
				<div class="card rounded-3 shadow flex-grow-1">
					<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4 pb-2">
						<h4 class="mb-0">
							<LocaleText t="Peer Settings"></LocaleText>
						</h4>
						<button type="button" class="btn-close ms-auto" @click="this.$emit('close')"></button>
					</div>
					<div class="card-body px-4" v-if="this.data">
						<div class="d-flex flex-column gap-2 mb-4">
							<div class="d-flex align-items-center">
								<small class="text-muted">
									<LocaleText t="Public Key"></LocaleText>
								</small>
								<small class="ms-auto"><samp>{{this.data.id}}</samp></small>
							</div>
							<div>
								<label for="peer_name_textbox" class="form-label">
									<small class="text-muted">
										<LocaleText t="Name"></LocaleText>
									</small>
								</label>
								<input type="text" class="form-control form-control-sm rounded-3"
								       :disabled="this.saving"
								       v-model="this.data.name"
								       id="peer_name_textbox" placeholder="">
							</div>
							<div>
								<div class="d-flex position-relative">
									<label for="peer_private_key_textbox" class="form-label">
										<small class="text-muted"><LocaleText t="Private Key"></LocaleText> 
											<code>
												<LocaleText t="(Required for QR Code and Download)"></LocaleText>
											</code></small>
									</label>
									<a role="button" class="ms-auto text-decoration-none toggleShowKey"
									   @click="this.showKey = !this.showKey"
									>
										<i class="bi" :class="[this.showKey ? 'bi-eye-slash-fill':'bi-eye-fill']"></i>
									</a>
								</div>
								<input :type="[this.showKey ? 'text':'password']" class="form-control form-control-sm rounded-3"
								       :disabled="this.saving"
								       v-model="this.data.private_key"
								       id="peer_private_key_textbox"
								       style="padding-right: 40px">
							</div>
							<div>
								<label for="peer_allowed_ip_textbox" class="form-label">
									<small class="text-muted">
										<LocaleText t="Allowed IPs"></LocaleText>
										<code>
											<LocaleText t="(Required)"></LocaleText>
										</code></small>
								</label>
								<input type="text" class="form-control form-control-sm rounded-3"
								       :disabled="this.saving"
								       v-model="this.data.allowed_ip"
								       id="peer_allowed_ip_textbox">
							</div>

							<div>
								<label for="peer_endpoint_allowed_ips" class="form-label">
									<small class="text-muted">
										<LocaleText t="Endpoint Allowed IPs"></LocaleText>
										<code>
											<LocaleText t="(Required)"></LocaleText>
										</code></small>
								</label>
								<input type="text" class="form-control form-control-sm rounded-3"
								       :disabled="this.saving"
								       v-model="this.data.endpoint_allowed_ip"
								       id="peer_endpoint_allowed_ips">
							</div>
							<div>
								<label for="peer_DNS_textbox" class="form-label">
									<small class="text-muted">
										<LocaleText t="DNS"></LocaleText>
									</small>
								</label>
								<input type="text" class="form-control form-control-sm rounded-3"
								       :disabled="this.saving"
								       v-model="this.data.DNS"
								       id="peer_DNS_textbox">
							</div>
							<div class="accordion my-3" id="peerSettingsAccordion">
								<div class="accordion-item">
									<h2 class="accordion-header">
										<button class="accordion-button rounded-3 collapsed" type="button"
										        data-bs-toggle="collapse" data-bs-target="#peerSettingsAccordionOptional">
											<LocaleText t="Optional Settings"></LocaleText>
										</button>
									</h2>
									<div id="peerSettingsAccordionOptional" class="accordion-collapse collapse"
									     data-bs-parent="#peerSettingsAccordion">
										<div class="accordion-body d-flex flex-column gap-2 mb-2">
											<div>
												<label for="peer_preshared_key_textbox" class="form-label">
													<small class="text-muted">
														<LocaleText t="Pre-Shared Key"></LocaleText></small>
												</label>
												<input type="text" class="form-control form-control-sm rounded-3"
												       :disabled="this.saving"
												       v-model="this.data.preshared_key"
												       id="peer_preshared_key_textbox">
											</div>
											<div>
												<label for="peer_mtu" class="form-label"><small class="text-muted">
													<LocaleText t="MTU"></LocaleText>
												</small></label>
												<input type="number" class="form-control form-control-sm rounded-3"
												       :disabled="this.saving"
												       v-model="this.data.mtu"
												       id="peer_mtu">
											</div>
											<div>
												<label for="peer_keep_alive" class="form-label">
													<small class="text-muted">
														<LocaleText t="Persistent Keepalive"></LocaleText>
													</small>
												</label>
												<input type="number" class="form-control form-control-sm rounded-3"
												       :disabled="this.saving"
												       v-model="this.data.keepalive"
												       id="peer_keep_alive">
											</div>
										</div>
									</div>
								</div>
							</div>
							<div class="d-flex align-items-center gap-2">
								<button class="btn bg-secondary-subtle border-secondary-subtle text-secondary-emphasis rounded-3 shadow ms-auto px-3 py-2"
								        @click="this.reset()"
								        :disabled="!this.dataChanged || this.saving">
									<i class="bi bi-arrow-clockwise me-2"></i>
									<LocaleText t="Reset"></LocaleText>
								</button>

								<button class="btn bg-primary-subtle border-primary-subtle text-primary-emphasis rounded-3 px-3 py-2 shadow"
								        :disabled="!this.dataChanged || this.saving"
								        @click="this.savePeer()"
								>
									<i class="bi bi-save-fill me-2"></i>
									<LocaleText t="Save"></LocaleText>
								</button>
							</div>
							<hr>
							<div class="d-flex gap-2 align-items-center">
								<strong>
									<LocaleText t="Reset Data Usage"></LocaleText>
								</strong>
								<div class="d-flex gap-2 ms-auto">
									<button class="btn bg-primary-subtle text-primary-emphasis rounded-3 flex-grow-1 shadow-sm"
										@click="this.resetPeerData('total')"
									>
										<i class="bi bi-arrow-down-up me-2"></i>
										<LocaleText t="Total"></LocaleText>
									</button>
									<button class="btn bg-primary-subtle text-primary-emphasis rounded-3 flex-grow-1 shadow-sm"
									        @click="this.resetPeerData('receive')"
									>
										<i class="bi bi-arrow-down me-2"></i>
										<LocaleText t="Received"></LocaleText>
									</button>
									<button class="btn bg-primary-subtle text-primary-emphasis rounded-3  flex-grow-1 shadow-sm"
									        @click="this.resetPeerData('sent')"
									>
										<i class="bi bi-arrow-up me-2"></i>
										<LocaleText t="Sent"></LocaleText>
									</button>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
			
		</div>

	</div>
</template>

<style scoped>
.toggleShowKey{
	position: absolute;
	top: 35px;
	right: 12px;
}
</style>