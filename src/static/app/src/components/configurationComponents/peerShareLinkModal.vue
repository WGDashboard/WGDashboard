<script>
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import {fetchPost} from "@/utilities/fetch.js";
import dayjs from "dayjs";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import VueDatePicker from '@vuepic/vue-datepicker';
import LocaleText from "@/components/text/localeText.vue";
import PeerShareWithEmail from "@/components/configurationComponents/peerShareLinkComponents/peerShareWithEmail.vue";


export default {
	name: "peerShareLinkModal",
	props: {
		selectedPeer: Object
	},
	components: {
		PeerShareWithEmail,
		LocaleText,
		VueDatePicker
	},
	data(){
		return {
			dataCopy: undefined,
			loading: false,
			fullscreen: false,
			shareWithEmail: false
		}
	},
	setup(){
		const store = DashboardConfigurationStore();
		return {store}
	},
	mounted() {
		this.dataCopy = JSON.parse(JSON.stringify(this.selectedPeer.ShareLink)).at(0);
	},
	watch: {
		'selectedPeer.ShareLink': {
			deep: true,
			handler(newVal, oldVal){
				if (oldVal.length !== newVal.length){
					this.dataCopy = JSON.parse(JSON.stringify(this.selectedPeer.ShareLink)).at(0);
				}
			}
		}
	},
	
	methods: {
		startSharing(){
			this.loading = true;
			fetchPost("/api/sharePeer/create", {
				Configuration: this.selectedPeer.configuration.Name,
				Peer: this.selectedPeer.id,
				ExpireDate: dayjs().add(7, 'd').format("YYYY-MM-DD HH:mm:ss")
			}, (res) => {
				if (res.status){
					this.selectedPeer.ShareLink = res.data;
					this.dataCopy = res.data.at(0);
				}else{
					this.store.newMessage("Server", 
						"Share link failed to create. Reason: " + res.message, "danger")
				}
				this.loading = false;
			})
		},
		updateLinkExpireDate(){
			fetchPost("/api/sharePeer/update", this.dataCopy, (res) => {
				if (res.status){
					this.dataCopy = res.data.at(0)
					this.selectedPeer.ShareLink = res.data;
					this.store.newMessage("Server", "Link expire date updated", "success")
				}else{
					this.store.newMessage("Server",
						"Link expire date failed to update. Reason: " + res.message, "danger")
				}
				this.loading = false
			});
		},
		stopSharing(){
			this.loading = true;
			this.dataCopy.ExpireDate = 	dayjs().format("YYYY-MM-DD HH:mm:ss")
			this.updateLinkExpireDate()
		},
		parseTime(modelData){
			if(modelData){
				this.dataCopy.ExpireDate = dayjs(modelData).format("YYYY-MM-DD HH:mm:ss");
			}else{
				this.dataCopy.ExpireDate = undefined
			}
			this.updateLinkExpireDate()
		}
	},
	computed: {
		getUrl(){
			const crossServer = this.store.getActiveCrossServer();
			if(crossServer){
				return `${crossServer.host}/${this.$router.resolve(
					{path: "/share", query: {"ShareID": this.dataCopy.ShareID}}).href}`
			}
			
			return window.location.origin 
				+ window.location.pathname 
				+ this.$router.resolve(
					{path: "/share", query: {"ShareID": this.dataCopy.ShareID}}).href;
		}
	}
}
</script>

<template>
	<div class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0 overflow-y-scroll">
		<div class="container d-flex h-100 w-100">
			<div class="m-auto modal-dialog-centered dashboardModal" :style="[ this.fullscreen ? 'width: 100%' : 'width: 700px']">
				<div class="card rounded-3 shadow flex-grow-1">
					<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4">
						<h4 class="mb-0">
							<LocaleText t="Share Peer"></LocaleText>
						</h4>
						<button type="button" class="btn-close ms-auto" @click="this.$emit('close')"></button>
					</div>
					<div class="card-body px-4 pb-4" v-if="this.selectedPeer.ShareLink">
						<div v-if="!this.dataCopy">
							<h6 class="mb-3 text-muted">
								<LocaleText t="Currently the peer is not sharing"></LocaleText>
							</h6>
							<button 
								@click="this.startSharing()"
								:disabled="this.loading"
								class="w-100 btn bg-success-subtle text-success-emphasis border-1 border-success-subtle rounded-3 shadow-sm">
								<span :class="{'animate__animated animate__flash animate__infinite animate__slower': this.loading}">
									<i class="bi bi-send-fill me-2" ></i>
								</span>
								<LocaleText t="Sharing..." v-if="this.loading"></LocaleText>
								<LocaleText t="Start Sharing" v-else></LocaleText>
							</button>
						</div>
						<div v-else>
							<div v-if="!shareWithEmail">
								<div class="d-flex gap-2 mb-4">
									<i class="bi bi-link-45deg"></i>
									<a :href="this.getUrl"
									   class="text-decoration-none" target="_blank">
										{{ getUrl }}
									</a>
								</div>
								<div class="d-flex flex-column gap-2 mb-3">
									<small>
										<i class="bi bi-calendar me-2"></i>
										<LocaleText t="Expire At"></LocaleText>
									</small>
									<VueDatePicker
										:is24="true"
										:min-date="new Date()"
										:model-value="this.dataCopy.ExpireDate"
										@update:model-value="this.parseTime" time-picker-inline
										format="yyyy-MM-dd HH:mm:ss"
										preview-format="yyyy-MM-dd HH:mm:ss"

										:dark="this.store.Configuration.Server.dashboard_theme === 'dark'"
									/>
								</div>
								<div class="d-flex gap-2 flex-column flex-sm-row">
									<button
										style="flex: 1 1 0"
										@click="this.stopSharing()"
										:disabled="this.loading"
										class="w-100 btn bg-danger-subtle text-danger-emphasis border-1 border-danger-subtle rounded-3 shadow-sm">
									<span :class="{'animate__animated animate__flash animate__infinite animate__slower': this.loading}">
										<i class="bi bi-send-slash-fill me-2" ></i>
									</span>
										<LocaleText t="Stop Sharing..." v-if="this.loading"></LocaleText>
										<LocaleText t="Stop Sharing" v-else></LocaleText>
									</button>
									<button
										style="flex: 1 1 0"
										@click="shareWithEmail = true"
										class="btn bg-primary-subtle text-primary-emphasis border-primary-subtle rounded-3">
										<i class="bi bi-envelope me-2"></i><LocaleText t="Share with Email"></LocaleText>
									</button>
								</div>
							</div>
							<Suspense v-else>
								<PeerShareWithEmail 
									@hide="shareWithEmail = false"
									@fullscreen="(f) => { this.fullscreen = f; }"
									:selectedPeer="selectedPeer" :dataCopy="dataCopy"></PeerShareWithEmail>
								<template #fallback>
									<h6 class="text-muted">
										<span class="spinner-border me-2 spinner-border-sm" role="status"></span>
										<LocaleText t="Checking SMTP Configuration..."></LocaleText>
									</h6>
								</template>
							</Suspense>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>