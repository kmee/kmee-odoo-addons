odoo.define("guep_sale.ApplicationForm", function (require) {
    "use strict";

    const publicWidget = require("web.public.widget");
    const Dialog = require("web.Dialog");

    const core = require("web.core");
    const _t = core._t;

    publicWidget.registry.ApplicationForm = publicWidget.Widget.extend({
        selector: ".o_hr_application",
        events: {
            "submit .o_application_form": "_onSubmitApplication",
            "click .o_application_add_dependent": "_onAddDependent",
            "click .o_application_remove_dependent": "_onRemoveDependent",
        },

        start: function () {
            this._super.apply(this, arguments);

            this.applicationId = this.$el.find('input[name="applicant_id"]').val();
        },

        /**
         * Handles form submission.
         * @param {Event} ev
         */
        _onSubmitApplication: async function (ev) {
            ev.preventDefault();

            return this._rpc({
                route: `/application/${this.applicationId}/form/submit`,
                params: {...(await this._getSerializedFormData())},
            }).then((result) => {
                let $dialogTitle = "";
                let $dialogContentMessage = "";

                if (result) {
                    $dialogTitle = _t("Success");
                    $dialogContentMessage = $("<span>", {
                        text: _t("Application saved successfully!"),
                    });
                } else {
                    $dialogTitle = _t("Error");
                    $dialogContentMessage = $("<span>", {
                        text: _t("Error saving the application. Try again later."),
                    });
                }

                return new Dialog(this, {
                    title: $dialogTitle,
                    size: "medium",
                    $content: $("<div>").append($dialogContentMessage),
                    buttons: [
                        {
                            text: _t("Cancel"),
                            close: true,
                        },
                    ],
                }).open();
            });
        },

        /**
         * Adds a new dependent form dynamically.
         */
        _onAddDependent: function () {
            const dependentContainer = this.$(".o_dependents_container");
            const index = dependentContainer.children().length + 1;

            const dependentForm = `
                <div class="dependent mb-3 p-3 border rounded">
                    <h6>Dependente ${index}</h6>
                    <div class="row">
                        <div class="col-6 mb-2">
                            <label class="form-label">Nome</label>
                            <input type="text" class="form-control dependent_name" required="1" />
                        </div>
                        <div class="col-6 mb-2">
                            <label class="form-label">Data de Nascimento</label>
                            <input type="date" class="form-control dependent_date_of_birth" required="1" />
                        </div>
                    </div>
                    <button type="button" class="btn btn-danger btn-sm o_application_remove_dependent">Remover</button>
                </div>
            `;
            dependentContainer.append(dependentForm);
        },

        /**
         * Removes a dependent form dynamically.
         * @param {Event} ev
         */
        _onRemoveDependent: function (ev) {
            $(ev.target).closest(".dependent").remove();
        },

        /**
         * Converts a file to a Base64 string.
         * @param {File} file
         * @returns {Promise<String>} Base64 string
         */
        _getFileBase64: function (file) {
            if (!file) return Promise.resolve(null);

            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.readAsDataURL(file);
                reader.onload = () => resolve(reader.result.slice(28));
                reader.onerror = reject;
            });
        },

        /**
         * Collects data from dependents dynamically.
         * @returns {Array} Dependents data
         */
        _getDependentsData: function () {
            return this.$(".dependent")
                .map((_, element) => {
                    const $dependent = $(element);
                    return {
                        name: $dependent.find(".dependent_name").val(),
                        date_of_birth: $dependent
                            .find(".dependent_date_of_birth")
                            .val(),
                    };
                })
                .get();
        },

        /**
         * Collects address data.
         * @returns {Array} Address data
         */
        _getAddressData: function () {
            return {
                street: this.$("input#street").val(),
                street_number: this.$("input#street_number").val(),
                street2: this.$("input#street_2").val(),
                district: this.$("input#district").val(),
                zip: this.$("input#cep").val(),
                city_id: this.$("input#city").val(),
                state_id: this.$("input#state").val(),
            };
        },

        /**
         * Collects bank data.
         * @returns {Array} Bank data
         */
        _getBankData: function () {
            return {
                bank_id: parseInt(this.$("select#bank").val(), 10),
                bra_number: this.$("input#agency").val(),
                acc_number: this.$("input#account").val(),
            };
        },

        /**
         * Serializes the form data into a structured object.
         * @returns {Promise<Object>} Serialized form data
         */
        _getSerializedFormData: async function () {
            const formData = {
                name: this.$("input#name").val(),
                birthday: this.$("input#date_of_birth").val(),
                rg: this.$("input#rg").val(),
                cpf: this.$("input#cpf").val(),
                ethnicity: parseInt(this.$("select#ethnicity").val(), 10),
                nationality_id: parseInt(this.$("select#nationality").val(), 10),
                partner_phone: this.$("input#phone").val(),
                email_from: this.$("input#email").val(),
                father_name: this.$("input#father_name").val(),
                mother_name: this.$("input#mother_name").val(),
                creservist: this.$("input#reservist").val(),
                pis_pasep: this.$("input#pis").val(),
                certificate: this.$("select#education").val(),
                voter_title: this.$("input#voter_title").val(),
                voter_zone: this.$("input#voter_zone").val(),
                voter_section: this.$("input#voter_section").val(),
                rg_file: await this._getFileBase64(this.$("#rg_file")[0].files[0]),
                cnh_file: await this._getFileBase64(this.$("#cnh_file")[0].files[0]),
                voter_title_file: await this._getFileBase64(
                    this.$("#voter_title_file")[0].files[0]
                ),
                study_proof_file: await this._getFileBase64(
                    this.$("#study_proof_file")[0].files[0]
                ),
                address_proof_file: await this._getFileBase64(
                    this.$("#address_proof_file")[0].files[0]
                ),
                reservist_file: await this._getFileBase64(
                    this.$("#reservist_file")[0].files[0]
                ),
                pis_file: await this._getFileBase64(this.$("#pis_file")[0].files[0]),
                address: this._getAddressData(),
                bank: this._getBankData(),
                dependents: this._getDependentsData(),
            };
            return formData;
        },
    });
});
