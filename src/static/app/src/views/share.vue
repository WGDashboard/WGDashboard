<script>
import {useRoute} from "vue-router";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {fetchGet} from "@/utilities/fetch.js";
import {computed, onMounted, ref} from "vue";
import QRCode from "qrcode";
import LocaleText from "@/components/text/localeText.vue";
import {initSystemThemeWatcher, resolveTheme} from "@/utilities/theme.js";

export default {
	name: "share",
	components: {LocaleText},
	async setup(){
		const route = useRoute();
		const loaded = ref(false)
		const store = DashboardConfigurationStore();
		const theme = ref("dark");
		const peerConfiguration = ref(undefined);
		const blob = ref(new Blob())
		await fetchGet("/api/getDashboardTheme", {}, (res) => {
			theme.value = res.data
		});
		
		const id = route.query.ShareID
		if(id === undefined || id.length === 0){
			peerConfiguration.value = undefined
			loaded.value = true;
		}else{
			await fetchGet("/api/sharePeer/get", {
				ShareID: id
			}, (res) => {
				if (res.status){
					peerConfiguration.value = res.data;
					blob.value = new Blob([peerConfiguration.value.file], { type: "text/plain" });
				}else{
					peerConfiguration.value = undefined
				}
				loaded.value = true;
			})
		}
		const resolvedTheme = computed(() => resolveTheme(theme.value))
		onMounted(() => {
			initSystemThemeWatcher();
		})
		return {store, theme, resolvedTheme, peerConfiguration, blob}
	},
	mounted() {
		if(this.peerConfiguration){
			QRCode.toCanvas(document.querySelector("#qrcode"), this.peerConfiguration.file,  (error) => {
				if (error) console.error(error)
			})
		}
	},
	methods:{
		download(){
			const blob = new Blob([this.peerConfiguration.file], { type: "text/plain" });
			const jsonObjectUrl = URL.createObjectURL(blob);
			const filename = `${this.peerConfiguration.fileName}.conf`;
			const anchorEl = document.createElement("a");
			anchorEl.href = jsonObjectUrl;
			anchorEl.download = filename;
			anchorEl.click();
		}
	},
	computed:{
		getBlob(){
			return URL.createObjectURL(this.blob)
		}
	}
}
</script>

<template>
	<div class="container-fluid login-container-fluid d-flex main pt-5 overflow-scroll"
	     :data-bs-theme="this.resolvedTheme">
		<div class="m-auto text-body" style="width: 500px">
			<div class="text-center position-relative" style=""
			     v-if="!this.peerConfiguration">
				<div class="animate__animated animate__fadeInUp">
					<h1 style="font-size: 20rem; filter: blur(1rem); animation-duration: 7s"
					    class="animate__animated animate__flash animate__infinite">
						<i class="bi bi-file-binary"></i>
					</h1>
				</div>
				<div class="position-absolute w-100 h-100 top-0 start-0 d-flex animate__animated animate__fadeInUp"
					style="animation-delay: 0.1s;"
				>
					<h3 class="m-auto">
						<LocaleText t="Oh no... This link is either expired or invalid."></LocaleText>
					</h3>
				</div>
			</div>
			<div v-else class="d-flex align-items-center flex-column gap-3">
				<div class="h1 dashboardLogo text-center animate__animated animate__fadeInUp">
					<h6>WGDashboard</h6>
					<LocaleText t="Scan QR Code with the WireGuard App to add peer"></LocaleText>
				</div>
				<canvas id="qrcode" class="rounded-3 shadow animate__animated animate__fadeInUp mb-3" ref="qrcode"></canvas>
				<p class="text-muted animate__animated animate__fadeInUp mb-1"
				   style="animation-delay: 0.2s;"> 
					<LocaleText t="or click the button below to download the "></LocaleText>
					<samp>.conf</samp>
					<LocaleText t=" file"></LocaleText>
				</p>
				<a 
					:download="this.peerConfiguration.fileName + '.conf'"
					:href="getBlob"
					class="btn btn-lg bg-primary-subtle text-primary-emphasis border-1 border-primary-subtle animate__animated animate__fadeInUp shadow-sm"
				        style="animation-delay: 0.25s;"
					
				>
					<i class="bi bi-download"></i>
				</a>
			</div>
		</div>
	</div>
</template>

<style scoped>
	.animate__fadeInUp{
		animation-timing-function: cubic-bezier(0.42, 0, 0.22, 1.0)
	}
</style>
