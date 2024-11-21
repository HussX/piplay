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
                    property var provider: liveImageProviders[index]
                    Component.onCompleted: {
                        if (provider) {
                            console.log("Connecting to image provider for index:", index);
                            provider.imageChanged.connect(reload);
                            //provider.ready.connect(onReady);
                        } else {
                            console.error("Image provider not found for index:", index);
                        }
                    }
                    //function onReady() {
                    //    provider.ready = true;
                    //}
                    function reload() {
                        source = "image://live_" + index + "/" + index + "?timestamp=" + Date.now();
                    }
                }
            }
        }
    }
}
