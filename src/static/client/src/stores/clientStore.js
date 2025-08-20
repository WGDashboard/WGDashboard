import {defineStore} from "pinia";
import {onMounted, reactive, ref} from "vue";
import {v4} from "uuid"
import dayjs from "dayjs";
import {axiosGet} from "@/utilities/request.js";


export const clientStore = defineStore('clientStore',  {
	state: () => ({
		serverInformation: {},
		notifications: [],
		configurations: [],
		clientProfile: {
			Email: "",
			SignInMethod: "",
			Profile: {}
		}
	}),
	actions: {
		newNotification(content, status){
			this.notifications.push({
				id: v4().toString(),
				status: status,
				content: content,
				time: dayjs(),
				show: true
			})
		},
		async getClientProfile(){
			const data = await axiosGet('/api/settings/getClientProfile')
			if (data){
				this.clientProfile = data.data
			}else{
				this.newNotification("Failed to fetch client profile", "danger")
			}
		},
		async getConfigurations(){
			const data = await axiosGet("/api/configurations")
			if (data){
				this.configurations = data.data
			}else{
				this.newNotification("Failed to fetch configurations", "danger")
			}
		}
	}
})