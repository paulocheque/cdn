/*
http://learn.jquery.com/plugins/basic-plugin-creation/

Example of Usage:

.progress { position:relative; width:300px; border: 1px solid #ddd; border-radius: 3px; margin-top:5px; margin-bottom:5px; }
.bar { background-color: #B4F5B4; width:0%; height:20px; border-radius: 3px; }
.bar-error { background-color: #FF0000; }
.percent { position:absolute; display:inline-block; top:3px; left:48%; }

<script src="/static/js/jquery-2.0.3.min.js"></script>
<script src="/static/js/secret-data-table.js"></script>
<script language="JavaScript">
$(document).ready(function() {
    var secretTable = new SecretDataTable({
        table: $("#table-list"),
        columns: [
            function(data, id) { return linkify(data.description) },
            function(data, id) { return data.tags },
            function(data, id) {
                var button = $("<button/>");
                button.click(function() {
                    // custom action
                });
                return button;
            },
        ],
        formCreate: $("#form-create"),
        formUpdate: $("#form-create"),
        create: true,
        update: true,
        del: true,
        log: false,
        onTableLoad: function(table){},
        onCreate: function(table, data){ table.createLine(new Date().getTime(), data); },
        onUpdate: function(table, id, data){ table.updateLine(id, data); },
        onCreateOrUpdate: function(table, id, data){ table.createOrUpdateLine(data._id || id, data); },
        onDelete: function(table, id, data){ table.deleteLine(id, data); },
        onTableChange: function(table){},
        onModalReady: function(modal){}
    });
});
</script>
*/
(function() {
    htmlEscape = function(text) {
        return text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
    };

    createModal = function(id, title, content) {
        var modal = $("<div/>").attr("id", "modal-" + id).attr("class", "modal fade");
        var divDialog = $("<div/>").attr("class", "modal-dialog");
        var divContent = $("<div/>").attr("class", "modal-content");
        var divHeader = $("<div/>").attr("class", "modal-header");
        var divBody = $("<div/>").attr("class", "modal-body");
        var divFooter = $("<div/>").attr("class", "modal-footer");
        divHeader.append($("<button/>").attr("type", "button").attr("class", "close").attr("aria-hidden", "true").attr("data-dismiss", "modal").html("&times;"));
        divHeader.append($("<h4/>").attr("class", "modal-title").html(title));
        if (content) {
            content.css("display", "block");
            divBody.append(content);
        }
        divFooter.append($("<button/>").attr("type", "button").attr("class", "btn btn-default").attr("data-dismiss", "modal").html("Close"));
        divContent.append(divHeader);
        divContent.append(divBody);
        divContent.append(divFooter);
        divDialog.append(divContent);
        modal.append(divDialog);
        modal.attr('tabindex', -1); // fix bootstrap keyboard ESC issue
        modal.on('hidden.bs.modal', function () {
            $(this).data('bs.modal', null);
            modal.remove();
        });
        modal.on('shown.bs.modal', function() {
            var firstInput = modal.find('input')[0]
            if (firstInput) firstInput.focus();
        });
        return modal;
    };

    createCreateButton = function(table) {
        var button = $("<button/>").attr("type", "button").attr("class", "btn btn-primary").html('<span class="glyphicon glyphicon-pencil"> New</span>');
        var onclick = function() {
            var form = table.settings.formCreate.clone(false);
            form.on('submit', function (e) {
                e.preventDefault();
                if (table.settings.onCreate) {
                    var formData = table.serializeFormData($(this).serializeArray(), table.settings.htmlFields);
                    table.settings.onCreate(table, formData);
                }
            });

            var modal = createModal("new", "New record", form);
            modal.modal({});
            if (table.settings.onModalReady) {
                table.settings.onModalReady(modal);
            }
        };
        button.click(onclick);
        return button;
    };

    createUpdateButton = function(table, id, data) {
        var button = $("<button/>").attr("type", "button").attr("class", "btn btn-default btn-xs").html('<span class="glyphicon glyphicon-edit"></span>');
        var onclick = function() {
            var form = table.settings.formUpdate.clone(false);
            for (var key in data) {
                form.find("[name='" + key + "']").val(data[key]);
            }
            form.on('submit', function (e) {
                e.preventDefault();
                if (table.settings.onUpdate) {
                    var formData = table.serializeFormData($(this).serializeArray(), table.settings.htmlFields);
                    table.settings.onUpdate(table, id, formData);
                }
            });

            var modal = createModal(id, "Editing <small>" + id + "</small>", form);
            modal.modal({});
            if (table.settings.onModalReady) {
                table.settings.onModalReady(modal);
            }
        };
        button.click(onclick);
        return button;
    };

    createDeleteForm = function(table, id, data) {
        var form = $("<form>").attr("method", "delete").attr("class", "form-delete");
        form.append('<button type="submit" class="btn btn-default btn-xs"><span class="glyphicon glyphicon-trash"></span></button>');
        form.on('submit', function (e) {
            e.preventDefault();
            if (table.settings.onDelete) {
                table.settings.onDelete(table, id, data);
            }
        });
        return form;
    };

    createUploadFilesButton = function(form, action) {
        var button = $("<button/>").attr("type", "button").attr("class", "btn btn-default btn-xs").html('<span class="fa fa-picture-o"></span>');
        var onclick = function() {
            form = form.clone(false);
            form.attr("enctype", "multipart/form-data");
            if (action) {
                form.attr("action", action);
            }
            var bar = $("<div/>").attr("class", "progress").append($("<div/>").attr("class", "bar")).append($("<div/>").attr("class", "percent"));
            form.css("display", "block");
            var div = $("<div/>").append(form).append($("<p/>").append(bar));
            var modal = createModal("upload-images", "Upload images", div);
            form.ajaxForm({
                beforeSend: function() {
                    var percentVal = '0%';
                    var bar = $(".bar");
                    bar.width(percentVal);
                    var percent = $(".percent");
                    percent.html(percentVal);
                },
                uploadProgress: function(event, position, total, percentComplete) {
                    var percentVal = percentComplete + '%';
                    var bar = $(".bar");
                    bar.width(percentVal);
                    var percent = $(".percent");
                    percent.html(percentVal);
                },
                success: function(response) {
                    var percentVal = '100%';
                    var bar = $(".bar");
                    bar.width(percentVal);
                    var percent = $(".percent");
                    percent.html(response);
                    modal.modal('hide');
                },
                error: function(response) {
                    var percent = $(".percent");
                    percent.html(response['statusText']);
                    $(".bar").addClass("bar-error");
                }
            });
            modal.modal({});
        };
        button.click(onclick);
        return button;
    };

    createLogButton = function(data) {
        var button = $("<button/>").attr("type", "button").attr("class", "btn btn-default btn-xs").html('<span class="glyphicon glyphicon-edit"></span>');
        var onclick = function() {
            console.log(data);
        };
        button.click(onclick);
        return button;
    };

    var SecretDataTable = function(options) {
        this.settings = $.extend({
            table: null,
            columns: [],
            formCreate: $("<input/>"),
            formUpdate: $("<input/>"),
            create: true,
            update: true,
            del: true,
            log: false,
            htmlFields: [],
            onTableLoad: function(table){},
            onCreate: function(table, data){ table.createLine(data._id, data); },
            onUpdate: function(table, id, data){ table.updateLine(data); },
            onCreateOrUpdate: function(table, id, data){ table.createOrUpdateLine(data._id || id, data); },
            onDelete: function(table, id, data){ table.deleteLine(data); },
            onTableChange: function(table){},
            onModalReady: function(modal){}
        }, options);
        // Compatibility
        if (this.settings.formEdit) {
            this.settings.formUpdate = this.settings.formEdit;
        }
        if (this.settings.edit) {
            this.settings.update = this.settings.edit;
        }
        // console.debug(this.settings);

        var weakThis = this;

        this.serializeFormData = function(originalFormData, htmlFields) {
            htmlFields = htmlFields || [];
            var formData = {};
            originalFormData.map(function(x) {
                if ($.inArray(x.name, htmlFields) !== -1) {
                    formData[x.name] = x.value;
                } else {
                    formData[x.name] = htmlEscape(x.value);
                }
            });
            return formData;
        }

        this._getColumnText = function(i, data, id) {
            try {
                return weakThis.settings.columns[i](data, id);
            } catch(e) {
                console.error(e);
                return "?";
            }
        }

        this.createLine = function(id, data) {
            $("#modal-new").modal('hide');
            var newRow = $('<tr id="line-' + id + '">');
            for (var i in weakThis.settings.columns) {
                var text = weakThis._getColumnText(i, data, id);
                var col = $("<td>");
                col.append(text);
                newRow.append(col);
            }
            if (weakThis.settings.update === true && weakThis.settings.formUpdate) {
                var button = createUpdateButton(weakThis, id, data);
                var col = $("<td>");
                col.append(button);
                newRow.append(col);
            }
            if (weakThis.settings.del === true) {
                var form = createDeleteForm(weakThis, id, data);
                var col = $("<td>");
                col.append(form);
                newRow.append(col);
            }
            if (weakThis.settings.log === true) {
                var button = createLogButton(data);
                var col = $("<td>");
                col.append(button);
                newRow.append(col);
            }
            weakThis.settings.table.find("tbody:last").append(newRow);
            if (weakThis.settings.onTableChange) {
                weakThis.settings.onTableChange(weakThis);
            }
        }

        this.updateLine = function(id, data) {
            $("#modal-" + id).modal('hide');
            var line = weakThis.settings.table.find("#line-" + id);
            var columns = line.find("td");
            for (var i in weakThis.settings.columns) {
                var text = weakThis._getColumnText(i, data, id);
                var column = columns.eq(i);
                column.html(text);
                if (typeof column.effect === 'function') {
                    column.effect("highlight", {color:"#aaccff"}, 1000);
                } else {
                    column.fadeOut().fadeIn();
                }
            }
            if (weakThis.settings.onTableChange) {
                weakThis.settings.onTableChange(weakThis);
            }
        }

        this.createOrUpdateLine = function(id, data) {
            $("#modal-" + id).modal('hide');
            var line = weakThis.settings.table.find("#line-" + id);
            if (line.length == 0) {
                weakThis.createLine(id, data);
            } else {
                weakThis.updateLine(id, data);
            }
        }

        this.deleteLine = function(id, data) {
            var line = weakThis.settings.table.find("#line-" + id);
            line.fadeOut().remove();
            if (weakThis.settings.onTableChange) {
                weakThis.settings.onTableChange(weakThis);
            }
        }

        this.getLines = function() {
            return weakThis.settings.table.find("tr[id^=line-]");
        }

        this.getLinesIds = function() {
            var ids = [];
            var lines = weakThis.getLines();
            for (var i = 0; i < lines.length; i++) {
                var line = lines[i];
                the_id = line.id.replace("line-", "");
                ids.push(the_id);
            }
            return ids;
        }

        this.getColumn = function(index) {
            var lines = weakThis.getLines();
            var columns = [];
            for (var i = 0; i < lines.length; i++) {
                var line = lines[i];
                if (line) {
                    var column = line.cells[index]
                    if (column) {
                        columns.push(column.innerText);
                    }
                }
            }
            return columns;
        }

        this.clear = function() {
            var ids = weakThis.getLinesIds();
            for (var i = 0; i < ids.length; i++) {
                var line = ids[i];
                weakThis.deleteLine(line);
            }
        }

        if (weakThis.settings.create === true && weakThis.settings.formCreate) {
            var button = createCreateButton(weakThis);
            var newHead = $("<thead/>").append(button).append("<br/><br/>");
            weakThis.settings.table.prepend(newHead);
        }

        if (weakThis.settings.onTableLoad) {
            weakThis.settings.onTableLoad(weakThis);
        }

        return weakThis;
    };

    if(!window.SecretDataTable) { window.SecretDataTable = SecretDataTable };
    if(!window.htmlEscape) { window.htmlEscape = htmlEscape };
    if(!window.createModal) { window.createModal = createModal };

})();