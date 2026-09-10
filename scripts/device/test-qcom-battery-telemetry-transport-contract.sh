#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-}
[ -n "$source_dir" ] || {
	echo 'FAIL set SOURCE_DIR to the pinned Linux 7.1.4 source' >&2
	exit 1
}

[ -d "$source_dir/.git" ]
[ "$(git -C "$source_dir" rev-parse HEAD)" = \
	7a5cef0db4795d9d453a12e0f61b5b7634fc4d40 ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]

qrtr_makefile=$source_dir/net/qrtr/Makefile
qrtr_core=$source_dir/net/qrtr/af_qrtr.c
qrtr_transport=$source_dir/net/qrtr/smd.c
pdr=$source_dir/drivers/soc/qcom/pdr_interface.c
mapper=$source_dir/drivers/soc/qcom/qcom_pd_mapper.c
pmic=$source_dir/drivers/soc/qcom/pmic_glink.c
common=$source_dir/drivers/remoteproc/qcom_common.c

for source in "$qrtr_makefile" "$qrtr_core" "$qrtr_transport" "$pdr" \
	"$mapper" "$pmic" "$common"
do
	[ -r "$source" ]
done

grep -Eq '^qrtr-y[[:space:]]*:=[[:space:]]*af_qrtr[.]o ns[.]o$' \
	"$qrtr_makefile"
grep -Fq 'rc = qrtr_ns_init();' "$qrtr_core"
grep -Fq 'postcore_initcall(qrtr_proto_init);' "$qrtr_core"

grep -Fq '{ "IPCRTR" }' "$qrtr_transport"
grep -Fq 'qrtr_endpoint_register(&qdev->ep, QRTR_EP_NID_AUTO)' \
	"$qrtr_transport"
grep -Fq 'rpmsg_send(qdev->channel, skb->data, skb->len)' "$qrtr_transport"
grep -Fq 'MODULE_ALIAS("rpmsg:IPCRTR")' "$qrtr_transport"

grep -Fq 'adev->name = "pd-mapper";' "$common"
grep -Fq '{ .name = "qcom_common.pd-mapper" }' "$mapper"
grep -Fq '#define TMS_SERVREG_SERVICE "tms/servreg"' "$mapper"
grep -Fq '.domain = "msm/adsp/charger_pd"' "$mapper"
grep -Fq '.instance_id = 74' "$mapper"
grep -Fq 'qmi_add_server(&data->handle, QMI_SERVICE_ID_SERVREG_LOC,' \
	"$mapper"

mapper_handlers=$(awk '
	/^static const struct qmi_msg_handler qcom_pdm_msg_handlers\[\]/ {
		found = 1
	}
	found { print }
	found && /^};$/ { exit }
' "$mapper")
[ "$(printf '%s\n' "$mapper_handlers" | grep -c '^[[:space:]]*\.fn = ')" \
	-eq 2 ]
printf '%s\n' "$mapper_handlers" |
	grep -Fq '.fn = qcom_pdm_get_domain_list'
printf '%s\n' "$mapper_handlers" |
	grep -Fq '.fn = qcom_pdm_pfr'

grep -Fq 'qmi_add_lookup(&pdr->locator_hdl, QMI_SERVICE_ID_SERVREG_LOC, 1, 1)' \
	"$pdr"
grep -Fq 'qmi_add_lookup(&pdr->notifier_hdl, pds->service, 1,' "$pdr"
grep -Fq '.charger_pdr_service_name = "tms/servreg"' "$pmic"
grep -Fq '.charger_pdr_service_path = "msm/adsp/charger_pd"' "$pmic"
grep -Fq 'if (pg->pdr_state == SERVREG_SERVICE_STATE_UP && pg->ept)' "$pmic"

if grep -Eq \
	'power_supply|typec|regulator|nvmem|rtc_|block_device|filp_open|kernel_write|writel|regmap_write|gpio_set_value|pdr_restart_pd|rproc_(boot|shutdown)' \
	"$mapper" "$qrtr_transport"
then
	echo 'FAIL telemetry transport or PD mapper contains an unreviewed hardware/storage control path' >&2
	exit 1
fi

echo 'PASS QRTR name service is kernel-resident; the IPCRTR transport and SM8350 PD mapper provide only the audited PMIC-telemetry service path'
