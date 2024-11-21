import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15
import QtMultimedia 6.4
import QtQml.WorkerScript 6.4

ApplicationWindow {
    visible: true
    width: Screen.width
    height: Screen.height

    GridLayout {
        id: gridLayout
        width: parent.width
        height: parent.height
        columns: gridCols
        rows: gridRows

        Repeater {
            model: numberOfStreams

            Rectangle {
                color: "black"
                Layout.fillWidth: true
                Layout.fillHeight: true
                
                Image {  
                    id: opencvImage
                    anchors.fill: parent
                    fillMode: Image.Stretch  // Make sure fillMode is set correctly
                    source: "image://live_" + model.index + "/" + model.index
                    cache: false
                    
                    Component.onCompleted: {
                        var imageProvider = liveImageProviders[index]; // Get the provider directly
                        if (imageProvider) {
                            console.log("Connecting to image provider for index:", index);
                            imageProvider.imageChanged.connect(reload); // Connect to the signal
                        } else {
                            console.error("Image provider not found for index:", index);
                        }
                    }

                    function reload() {
                        source = "image://live_" + index + "/" + index + "?timestamp=" + Date.now();
                    }
                }

                Connections {
                    target: liveImageProviders[index]
                    function imageChanged(index) {
                        console.log("imageChanged signal received for index: " + index);
                        if (index === model.index) {
                            opencvImage.reload();
                        }
                    }
                }
            }
        }
    }
}
