<script>
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {v4} from "uuid";
import {fetchPost} from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";

export default {
	components: {LocaleText},
	props:{
		targetData: String,
		title: String,
		warning: false,
		warningText: "",
	},
	setup(){
		const store = DashboardConfigurationStore();
		const uuid = `input_${v4()}`;
		return {store, uuid};
	},
	data(){
		return{
			value:"",
			invalidFeedback: "",
			showInvalidFeedback: false,
			isValid: false,
			timeout: undefined,
			changed: false,
			updating: false,
		}
	},
	mounted() {
		this.value = this.store.Configuration.Peers[this.targetData];
	},
	computed: {
		isBoolean(){
			return typeof this.value === "boolean"
		}
	},
	methods:{
		async useValidation(){
			if(this.changed){
				await fetchPost("/api/updateDashboardConfigurationItem", {
					section: "Peers",
					key: this.targetData,
					value: this.value
				}, (res) => {
					if (res.status){
						this.isValid = true;
						this.showInvalidFeedback = false;
						this.store.Configuration.Peers[this.targetData] = this.value
						clearTimeout(this.timeout)
						this.timeout = setTimeout(() => this.isValid = false, 5000);

					}else{
						this.isValid = false;
						this.showInvalidFeedback = true;
						this.invalidFeedback = res.message
					}
					this.changed = false
					this.updating = false;
				})
			}
		}
	}
}
</script>

<template>
	<div class="form-group mb-2">
		<label :for="this.uuid" class="text-muted mb-1">
			<strong><small>
				<LocaleText :t="this.title"></LocaleText>
			</small></strong>
		</label>
		<div v-if="isBoolean" class="form-check form-switch">
			<input class="form-check-input" type="checkbox" role="switch"
			       v-model="this.value"
			       :id="this.uuid"
			       @change="this.changed = true; useValidation()"
			       :disabled="this.updating">
		</div>
		<input v-else type="text" class="form-control" 
		       :class="{'is-invalid': showInvalidFeedback, 'is-valid': isValid}"
		       :id="this.uuid"
		       v-model="this.value"
		       @keydown="this.changed = true"
		       @blur="useValidation()"
		       :disabled="this.updating"
		>
		<div class="invalid-feedback">{{this.invalidFeedback}}</div>
		<div class="px-2 py-1 text-warning-emphasis bg-warning-subtle border border-warning-subtle rounded-2 d-inline-block mt-1"
			v-if="warning"
		>
			<small><i class="bi bi-exclamation-triangle-fill me-2"></i>
				<LocaleText :t="warningText"></LocaleText>
			</small>
		</div>
	</div>
</template>

<style scoped>

</style>
