<script>
import LocaleText from "@/components/text/localeText.vue";

export default {
	name: "presharedKeyInput",
	components: {LocaleText},
	props: {
		data: Object,
		saving: Boolean,
		defaultEnabled: Boolean
	},
	data(){
		return{
			enable: false
		}
	},
	mounted() {
		const hasKey = !!(this.data && this.data.preshared_key && this.data.preshared_key.length > 0)
		if (hasKey || this.defaultEnabled){
			this.enable = true
		}
	},
	watch:{
		enable(){
			if (this.enable){
				if (!this.data.preshared_key){
					this.data.preshared_key = window.wireguard.generateKeypair().presharedKey
				}
			}else {
				this.data.preshared_key = ""
			}
		}
	}
}
</script>

<template>
<div>
	<div class="d-flex align-items-start">
		<label for="peer_preshared_key_textbox" class="form-label">
			<small class="text-muted">
				<LocaleText t="Pre-Shared Key"></LocaleText>
			</small>
		</label>
		<div class="form-check form-switch ms-auto">
			<input class="form-check-input" type="checkbox" role="switch" 
			       v-model="this.enable"
			       id="peer_preshared_key_switch">
		</div>
	</div>
	<input type="text" class="form-control form-control-sm rounded-3"
	       :disabled="this.saving || !this.enable"
	       v-model="this.data.preshared_key"
	       id="peer_preshared_key_textbox">
</div>
</template>

<style scoped>

</style>
