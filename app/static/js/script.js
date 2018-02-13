// FILE UPLOADER
$(function(){

    var ul = $('#upload ul');

    $('#drop a').click(function(){
        // Simulate a click on the file input button
        // to show the file browser dialog
        $(this).parent().find('input').click();
    });

    // Initialize the jQuery File Upload plugin
    $('#upload').fileupload({

        // This element will accept file drag/drop uploading
        dropZone: $('#drop'),

        // This function is called when a file is added to the queue;
        // either via the browse button, or via drag/drop:
        add: function (e, data) {

            // Show working animation
            var tpl = $('<li class="working"><input type="text" value="0" data-width="48" data-height="48"'+
                ' data-fgColor="#0788a5" data-readOnly="1" data-bgColor="#3e4043" /><p></p><span></span></li>');

            // Add the HTML to the UL element
            data.context = $('ul').html(tpl);

            // Initialize the knob plugin
            tpl.find('input').knob();

            // Listen for clicks on the cancel icon
            tpl.find('span').click(function(){

                if(tpl.hasClass('working')){
                    jqXHR.abort();
                }

                //tpl.fadeOut(function(){
                //    tpl.remove();
                //});

            });

            // Automatically upload the file once it is added to the queue
            var jqXHR = data.submit()
                .success(function (result, textStatus, jqXHR) {
                    // Show download icon
                    tpl.find('.cssload-loader').replaceWith('<a href="'+result['downloadable_file']+'" title="Download glTF file" class="download-icon"><img src="/static/img/download.png"></a>')
                    // Append the file name
                    tpl.find('p').text(getFilename(result['downloadable_file']));
                                //.append('<i>' + formatFileSize(data.files[0].size) + '</i>');

                    // Initialize model viewer
                    initViewer(result['processed_file']);
                })
                .error(function (jqXHR, textStatus, errorThrown) {
                    console.log(errorThrown)
                })
                // .complete(function (result, textStatus, jqXHR) {/* ... */});
        },

        progress: function(e, data){

            // Calculate the completion percentage of the upload
            var progress = parseInt(data.loaded / data.total * 100, 10);

            // Update the hidden input field and trigger a change
            // so that the jQuery knob plugin knows to update the dial
            data.context.find('input').val(progress).change();

            if(progress == 100){
                $('li').removeClass('working');
                $("#uploaded-items canvas").replaceWith('<div class="cssload-loader"></div>');

            }
        },

        fail:function(e, data){
            // Something has gone wrong!
            $('li').addClass('error');
            $('li').removeClass('working');
            if(e.type == 'fileuploadfail') {
                $('li p').text('Please upload an FBX, OBJ, or ZIP file')
            }
        }

    });


    // Prevent the default action when a file is dropped on the window
    $(document).on('drop dragover', function (e) {
        e.preventDefault();
    });


    // Helper function that formats the file sizes
    function formatFileSize(bytes) {
        if (typeof bytes !== 'number') {
            return '';
        }

        if (bytes >= 1000000000) {
            return (bytes / 1000000000).toFixed(2) + ' GB';
        }

        if (bytes >= 1000000) {
            return (bytes / 1000000).toFixed(2) + ' MB';
        }

        return (bytes / 1000).toFixed(2) + ' KB';
    }


    // Add CSS class when file is hovered over the dropzone
    $('#drop').on('dragover dragenter', function() {
        $('#drop').addClass('in');
    })
    .on('dragleave dragend drop', function() {
        $('#drop').removeClass('in');
    })


});

function getFileExtension(filename) {
    return filename.slice((filename.lastIndexOf(".") - 1 >>> 0) + 2);
}

// See: https://stackoverflow.com/a/424006
function getFilename(path) {
    return path.split('\\').pop().split('/').pop();
}


// MODEL VIEWER
function initViewer(glb_file) {

    container = document.getElementById( 'container' );
    camera = new THREE.PerspectiveCamera( 75, 350 / 233, 1, 2000 );
    camera.position.z = 100;

    scene = new THREE.Scene();
    scene.add(camera);

    // Add lights
    var directionalLight = new THREE.DirectionalLight( 0xdddddd );
    directionalLight.position.set( 0, 0, 1 ).normalize();
    camera.add( directionalLight );

    var ambientLight = new THREE.AmbientLight( 0x222222 );
    scene.add( ambientLight );

    var loader = new THREE.GLTFLoader();
    loader.load(glb_file, function ( gltf ) {

        scene.add( gltf.scene );

        gltf.animations; // Array<THREE.AnimationClip>
        gltf.scene; // THREE.Scene
        gltf.scenes; // Array<THREE.Scene>
        gltf.cameras; // Array<THREE.Camera>

        // Make model fit to canvas
        boundingBox = new THREE.Box3().setFromObject( gltf.scene );
        orbitControls = new THREE.OrbitControls( camera, container );
        boundingBoxMaxSize = Math.max( boundingBox.max.x - boundingBox.min.x , boundingBox.max.y - boundingBox.min.y, boundingBox.max.z - boundingBox.min.z ) * 0.01;
        gltf.scene.scale.divideScalar(boundingBoxMaxSize);
        newBoundingBox = new THREE.Box3().setFromObject( gltf.scene );
        cameraTargetY = (newBoundingBox.min.y + newBoundingBox.max.y) * 0.5;
        camera.position.y = cameraTargetY;
        orbitControls.target = new THREE.Vector3(0, cameraTargetY, 0);
        orbitControls.update();

        // Apply environment map to object and background
        var envMap = getEnvironmentMap();
        gltf.scene.traverse( function( node ) {
            if ( node.material && ( node.material.isMeshStandardMaterial ||
                ( node.material.isShaderMaterial && node.material.envMap !== undefined ) ) ) {
                node.material.envMap = envMap;
                node.material.needsUpdate = true;
            }
        });
        scene.background = envMap;

    },
    // Called when loading is in progress
    function ( xhr ) {

        console.log( ( xhr.loaded / xhr.total * 100 ) + '% loaded' );

    },
    // Called when loading has errors
    function ( error ) {

        console.log('An error occurred while loading the model');
        //$('li').addClass('error');
        //$('li p').text('An error occurred while loading the model');

    });

    renderer = new THREE.WebGLRenderer({antialias:true});
    renderer.setSize( 350, 233 );
    $('#container').html(renderer.domElement);
    animate();
}

function animate() {

    requestAnimationFrame( animate );
    render();

}

function render() {

    renderer.render( scene, camera );

}

// https://jaxry.github.io/panorama-to-cubemap/
function getEnvironmentMap() {
    var format = '.png';
    var loader = new THREE.CubeTextureLoader();
    loader.setPath( '/static/img/gradient-light/' );

    var textureCube = loader.load( [
        'px' + format, 'nx' + format,
        'py' + format, 'ny' + format,
        'pz' + format, 'nz' + format
    ] );

    return textureCube;
}