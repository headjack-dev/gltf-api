// TODO: Return error message when invalid file extension is uploaded
// TODO: Add model viewer
// TODO: Add About info

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

            var tpl = $('<li class="working"><input type="text" value="0" data-width="48" data-height="48"'+
                ' data-fgColor="#0788a5" data-readOnly="1" data-bgColor="#3e4043" /><p></p><span></span></li>');

            // Append the file name and file size
            tpl.find('p').text(data.files[0].name)
                         .append('<i>' + formatFileSize(data.files[0].size) + '</i>');

            // Add the HTML to the UL element
            data.context = tpl.appendTo(ul);

            // Initialize the knob plugin
            tpl.find('input').knob();

            // Listen for clicks on the cancel icon
            tpl.find('span').click(function(){

                if(tpl.hasClass('working')){
                    jqXHR.abort();
                }

                tpl.fadeOut(function(){
                    tpl.remove();
                });

            });

            // Automatically upload the file once it is added to the queue
            var jqXHR = data.submit()
                .success(function (result, textStatus, jqXHR) {
                    // Show download icon
                    tpl.find('.cssload-loader').replaceWith('<a href="'+result['glb_file']+'" title="Download glTF file" class="download-icon"><img src="img/download.png"></a>')
                    // TODO: Show in model viewer (replaces form header image). On click in list, that particular file is shown in the viewer.
                })
                .error(function (jqXHR, textStatus, errorThrown) {
                    var errors = jqXHR.responseJSON;
                    console.log(errors)
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
                data.context.removeClass('working');
                $("#uploaded-items canvas").replaceWith('<div class="cssload-loader"></div>');
            }
        },

        fail:function(e, data){
            // Something has gone wrong!
            data.context.addClass('error');
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


// MODEL VIEWER
window.onload=function(){
  init();
  animate();
}

function init() {

  container = document.getElementById( 'container' );
  camera = new THREE.PerspectiveCamera( 75, 350 / 300, 1, 2000 );
  camera.position.z = 100;

  scene = new THREE.Scene();
  scene.add(camera);

  var environmentMap = getEnvironmentMap();
  scene.background = environmentMap;

  // Add lights
  var directionalLight = new THREE.DirectionalLight( 0xdddddd );
  directionalLight.position.set( 0, 0, 1 ).normalize();
  camera.add( directionalLight );

  var ambientLight = new THREE.AmbientLight( 0x222222 );
  scene.add( ambientLight );

  var loader = new THREE.GLTFLoader();
  loader.load('img/boombox/BoomBox.gltf', function ( gltf ) {

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

    },
    // Called when loading is in progress
    function ( xhr ) {

        console.log( ( xhr.loaded / xhr.total * 100 ) + '% loaded' );

    },
    // Called when loading has errors
    function ( error ) {

        console.log( 'An error happened loading the model' );

    }
  );

  renderer = new THREE.WebGLRenderer({antialias:true});
  renderer.setSize( 350, 300 );
  container.appendChild( renderer.domElement );

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
    loader.setPath( 'img/gradient/' );

    var textureCube = loader.load( [
        'posx' + format, 'negx' + format,
        'posy' + format, 'negy' + format,
        'posz' + format, 'negz' + format
    ] );

    return textureCube;
}

function generateBackground() {

	var size = 512;

	// create canvas
	canvas = document.createElement( 'canvas' );
	canvas.width = size;
	canvas.height = size;

	// get context
	var context = canvas.getContext( '2d' );

	// draw gradient
	context.rect( 0, 0, size, size );
	var gradient = context.createLinearGradient( 0, 0, size, size );
	gradient.addColorStop(0, '#99ddff'); // light blue
	gradient.addColorStop(1, '#ffff00'); // dark blue
	context.fillStyle = gradient;
	context.fill();

	return canvas;

}


/*
// Create an empty scene
var scene = new THREE.Scene();

// Create a basic perspective camera
var camera = new THREE.PerspectiveCamera( 75, window.innerWidth/window.innerHeight, 0.1, 1000 );
camera.position.z = 4;

// Create a renderer with Antialiasing
var renderer = new THREE.WebGLRenderer({antialias:true});

// Configure renderer clear color
renderer.setClearColor("#000000");

// Configure renderer size
renderer.setSize( window.innerWidth, window.innerHeight );

// Append Renderer to DOM
document.body.appendChild( renderer.domElement );

// ------------------------------------------------
// FUN STARTS HERE
// ------------------------------------------------

// Create a Cube Mesh with basic material
var geometry = new THREE.BoxGeometry( 1, 1, 1 );
var material = new THREE.MeshBasicMaterial( { color: "#433F81" } );
var cube = new THREE.Mesh( geometry, material );

// Add cube to Scene
scene.add( cube );

// Render Loop
var render = function () {
  requestAnimationFrame( render );

  cube.rotation.x += 0.01;
  cube.rotation.y += 0.01;

  // Render the scene
  renderer.render(scene, camera);
};

var loader = new THREE.GLTFLoader();

// Load a glTF resource
loader.load(
    // resource URL
    'img/model.glb',
    // called when the resource is loaded
    function ( gltf ) {

        scene.add( gltf.scene );

        gltf.animations; // Array<THREE.AnimationClip>
        gltf.scene; // THREE.Scene
        gltf.scenes; // Array<THREE.Scene>
        gltf.cameras; // Array<THREE.Camera>

    },
    // called when loading is in progresses
    function ( xhr ) {

        console.log( ( xhr.loaded / xhr.total * 100 ) + '% loaded' );

    },
    // called when loading has errors
    function ( error ) {

        console.log( 'An error happened' );

    }
);

render();


// glTF viewer
container = $('#container');
scene = new THREE.Scene();
scene.background = new THREE.Color( 0x222222 );
defaultCamera = new THREE.PerspectiveCamera( 45, container.offsetWidth / container.offsetHeight, 0.001, 1000 );
//defaultCamera.up = new THREE.Vector3( 0, 1, 0 );
scene.add( defaultCamera );
camera = defaultCamera;

renderer = new THREE.WebGLRenderer();
renderer.setSize( window.innerWidth, window.innerHeight );

var loader = new THREE.GLTFLoader();

// Load a glTF resource
loader.load(
    // resource URL
    'img/model.glb',
    // called when the resource is loaded
    function ( gltf ) {

        scene.add( gltf.scene );

        gltf.animations; // Array<THREE.AnimationClip>
        gltf.scene; // THREE.Scene
        gltf.scenes; // Array<THREE.Scene>
        gltf.cameras; // Array<THREE.Camera>

    },
    // called when loading is in progresses
    function ( xhr ) {

        console.log( ( xhr.loaded / xhr.total * 100 ) + '% loaded' );

    },
    // called when loading has errors
    function ( error ) {

        console.log( 'An error happened' );

    }
);*/
