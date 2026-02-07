<script>
import dayjs from "dayjs";
import {fetchPost} from "@/utilities/fetch.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import { VueDatePicker } from "@vuepic/vue-datepicker";
import LocaleText from "@/components/text/localeText.vue";
import {initSystemThemeWatcher, resolveTheme} from "@/utilities/theme.js";

export default {
	name: "newDashboardAPIKey",
	components: {LocaleText, VueDatePicker},
	data(){
		return{
			newKeyData:{
				ExpiredAt: dayjs().add(7, 'd').format("YYYY-MM-DD HH:mm:ss"),
				NeverExpire: false
			},
			submitting: false
		}
	},
	setup(){
		const store = DashboardConfigurationStore();
		return {store};
	},
	mounted() {
		initSystemThemeWatcher();
		console.log(this.newKeyData.ExpiredAt)
	},
	computed: {
		isDark(){
			return resolveTheme(this.store.Configuration.Server.dashboard_theme) === "dark"
		}
	},
	
	methods: {
		submitNewAPIKey(){
			this.submitting = true;
			fetchPost('/api/newDashboardAPIKey', this.newKeyData, (res) => {
				if (res.status){
					this.$emit('created', res.data);
					this.store.newMessage("Server", "API Key created", "success");
					this.$emit('close')
				}else{
					this.store.newMessage("Server", res.message, "danger")
				}
				this.submitting = false;
			})
		},
		fixDate(date){
			console.log(dayjs(date).format("YYYY-MM-DDTHH:mm:ss"))
			return dayjs(date).format("YYYY-MM-DDTHH:mm:ss")
		},
		parseTime(modelData){
			if(modelData){
				this.newKeyData.ExpiredAt = dayjs(modelData).format("YYYY-MM-DD HH:mm:ss");
			}else{
				this.newKeyData.ExpiredAt = undefined
			}
		}
	}
}
</script>

<template>
	<div class="position-absolute w-100 h-100 top-0 start-0 rounded-bottom-3 p-3 d-flex"
	     style="background-color: #00000060; backdrop-filter: blur(3px); z-index: 9999">
		<div class="card m-auto rounded-3 mt-5">
			<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4 pb-0">
				<h6 class="mb-0">
					<LocaleText t="Create API Key"></LocaleText>
				</h6>
				<button type="button" class="btn-close ms-auto" @click="this.$emit('close')"></button>
			</div>
			<div class="card-body d-flex gap-2 p-4 flex-column">
				<small class="text-muted">
					<LocaleText t="When should this API Key expire?"></LocaleText>
				</small>
				<div class="d-flex align-items-center gap-2">
					<VueDatePicker
						style="z-index: 9999"
						:is24="true"
						:min-date="new Date()"
						:model-value="this.newKeyData.ExpiredAt"
						@update:model-value="this.parseTime" time-picker-inline
						format="yyyy-MM-dd HH:mm:ss"
						preview-format="yyyy-MM-dd HH:mm:ss"
						:clearable="false"
						:disabled="this.newKeyData.NeverExpire || this.submitting"
						:dark="isDark"
					/>
				</div>
				<div class="form-check">
					<input class="form-check-input" type="checkbox"
					       v-model="this.newKeyData.NeverExpire" id="neverExpire" :disabled="this.submitting">
					<label class="form-check-label" for="neverExpire">
						<LocaleText t="Never Expire"></LocaleText> (<i class="bi bi-emoji-grimace-fill me-2"></i> 
						<LocaleText t="Don't think that's a good idea"></LocaleText>)
					</label>
				</div>
				<button class="ms-auto btn bg-success-subtle text-success-emphasis border-1 border-success-subtle rounded-3 shadow-sm"
					:class="{disabled: this.submitting}"
				        @click="this.submitNewAPIKey()"
				>
					<i class="bi bi-check-lg me-2" v-if="!this.submitting"></i>
					<LocaleText t="Creating..." v-if="this.submitting"></LocaleText>
					<LocaleText t="Create" v-else></LocaleText>
				</button>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>
