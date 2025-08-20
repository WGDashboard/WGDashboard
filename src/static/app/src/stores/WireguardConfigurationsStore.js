import {defineStore} from "pinia";
import {fetchGet} from "@/utilities/fetch.js";
import isCidr from "is-cidr";
import {GetLocale} from "@/utilities/locale.js";
import {fromString} from "css-color-converter";

export const WireguardConfigurationsStore = defineStore('WireguardConfigurationsStore', {
	state: () => ({
		Configurations: [],
        ConfigurationLoaded: false,
		searchString: "",
		ConfigurationListInterval: undefined,
        Filter: {
            HiddenTags: [],
            ShowAllPeersWhenHiddenTags: true
        },
        SortOptions: {
            Name: GetLocale("Name"),
            Status: GetLocale("Status"),
            'DataUsage.Total': GetLocale("Total Usage")
        },
        CurrentSort: {
            key: "Name",
            order: "asc"
        },
        CurrentDisplay: "List",
		PeerScheduleJobs: {
			dropdowns: {
				Field: [
					{
						display: GetLocale("Total Received"),
						value: "total_receive",
						unit: "GB",
						type: 'number'
					},
					{
						display: GetLocale("Total Sent"),
						value: "total_sent",
						unit: "GB",
						type: 'number'
					},
					{
						display: GetLocale("Total Usage"),
						value: "total_data",
						unit: "GB",
						type: 'number'
					},
					{
						display: GetLocale("Date"),
						value: "date",
						type: 'date'
					}
				],
				Operator: [
					// {
					// 	display: "equal",
					// 	value: "eq"
					// },
					// {
					// 	display: "not equal",
					// 	value: "neq"
					// },
					{
						display: GetLocale("larger than"),
						value: "lgt"
					},
					// {
					// 	display: "less than",
					// 	value: "lst"
					// },
				],
				Action: [
					{
						display: GetLocale("Restrict Peer"),
						value: "restrict"
					},
					{
						display: GetLocale("Delete Peer"),
						value: "delete"
					}
				]
			}
		}
	}),
    getters: {
        sortConfigurations(){
            return [...this.Configurations].sort((a, b) => {
                if (this.CurrentSort.order === 'desc') {
                    return this.dotNotation(a, this.CurrentSort.key) < this.dotNotation(b, this.CurrentSort.key) ?
                        1 : this.dotNotation(a, this.CurrentSort.key) > this.dotNotation(b, this.CurrentSort.key) ? -1 : 0;
                } else {
                    return this.dotNotation(a, this.CurrentSort.key) > this.dotNotation(b, this.CurrentSort.key) ?
                        1 : this.dotNotation(a, this.CurrentSort.key) < this.dotNotation(b, this.CurrentSort.key) ? -1 : 0;
                }
            })
        },
    },
	actions: {
		async getConfigurations(){
			await fetchGet("/api/getWireguardConfigurations", {}, (res) => {
				if (res.status)  {
                    this.Configurations = res.data
                }
                this.ConfigurationLoaded = true
			});
		},
        colorText(color){
            if (color){
                const cssColor = fromString(color)
                if (cssColor) {
                    const rgb = cssColor.toRgbaArray()
                    return +((rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 255000).toFixed(2) > 0.5 ? "#000":"#fff"
                }
            }
            return "#ffffff"
        },
        dotNotation(object, dotNotation){
            let result = dotNotation.split('.').reduce((o, key) => o && o[key], object)
            if (typeof result === "string"){
                return result.toLowerCase()
            }
            return result
        },
		regexCheckIP(ip){
			let regex = /((^\s*((([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))\s*$)|(^\s*((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))(%.+)?\s*$))/;
			return regex.test(ip)
		},
		checkCIDR(ip){
			return isCidr(ip) !== 0
		},
		checkWGKeyLength(key){
			const reg = /^[A-Za-z0-9+/]{43}=?=?$/;
			return reg.test(key)
		}
	},
    persist: {
        pick: [
            "CurrentSort", "CurrentDisplay", "Filter.ShowAllPeersWhenHiddenTags"
        ]
    }
});