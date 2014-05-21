$(document).ready(function () {
	
	var isDatasetCopy = $('body.package.copy').length > 0;
    if (isDatasetCopy) {
        var urlEditor = new CKAN.View.UrlEditor({
            slugType: 'package'
        });
        $('#resources').hide();
    }
	/*
    var isDatasetCopy = $('body.package.copy').length > 0;
    if (isDatasetCopy) {
      // Set up magic URL slug editor
      var urlEditor = new CKAN.View.UrlEditor({
        slugType: 'package'
      });
      $('#save').val(CKAN.Strings.addDataset);
      $("#title").focus();
      // Selectively enable the upload button
      var storageEnabled = $.inArray('storage',CKAN.plugins)>=0;
      if (storageEnabled) {
        $('li.js-upload-file').show();
      }
      */
//      // Backbone collection class
//      var CollectionOfResources = Backbone.Collection.extend({model: CKAN.Model.Resource});
//      // 'resources_json' was embedded into the page
//      var view = new CKAN.View.ResourceEditor({
//        collection: new CollectionOfResources(resources_json),
//        el: $('form#dataset-copy')
//      });
//      view.render();
/*
      $( ".drag-drop-list" ).sortable({
        distance: 10
      });
      $( ".drag-drop-list" ).disableSelection();

      CKAN.Utils.warnOnFormChanges($('form#dataset-copy'));
      var urlEditor = new CKAN.View.UrlEditor({
          slugType: 'package'
      });     
      */
    //}
/*
	var isDatasetCopy = $('body.package.copy').length > 0;
    if (isDatasetCopy) {
     // Set up magic URL slug editor
      CKAN.Utils.setupUrlEditor('package');
      $('#save').val(CKAN.Strings.addDataset);
      $("#title").focus();
      CKAN.Utils.setupUrlEditor('package',readOnly=true);
      // Selectively enable the upload button
      var storageEnabled = $.inArray('storage',CKAN.plugins)>=0;
      if (storageEnabled) {
        $('li.js-upload-file').show();
      }

      // Set up hashtag nagivigation
      // CKAN.Utils.setupDatasetEditNavigation();

      var _dataset = new CKAN.Model.Dataset(preload_dataset);
      var $el=$('form#dataset-edit');
      var view=new CKAN.View.DatasetEditForm({
        model: _dataset,
        el: $el
      });
      view.render();

      // Set up dataset delete button
      var select = $('select.dataset-delete');
      select.attr('disabled','disabled');
      select.css({opacity: 0.3});
      $('button.dataset-delete').click(function(e) {
        select.removeAttr('disabled');
        select.fadeTo('fast',1.0);
        $(e.target).css({opacity:0});
        $(e.target).attr('disabled','disabled');
        return false;
      });
    }
    */
});
